from datetime import timedelta, date
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
from credentials.models import MedicalAidPortalCredential
from credentials.admin import MedicalAidPortalCredentialAdmin
from practices.models import Practice
from patients.models import Patient, PatientScheme
from claims.models import Claim, ClaimLineItem, RpaSubmissionLog
from claims.tasks import submit_claim_rpa
from django.contrib.admin.sites import AdminSite
from unittest.mock import Mock


class CircuitBreakerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('admincb', 'admincb@example.com', 'secret123')
        self.cred = MedicalAidPortalCredential.objects.create(
            administrator='discovery',
            username='BUR-DISC-TEST',
            password='Password123!',
            bureau_bhf_number='BUR-99901',
            is_active=True,
            failure_threshold=3,
            cooldown_minutes=15
        )

    def test_initial_circuit_state_is_closed(self):
        self.assertEqual(self.cred.circuit_state, 'closed')
        self.assertEqual(self.cred.consecutive_failures, 0)
        is_avail, msg = self.cred.is_available()
        self.assertTrue(is_avail)
        self.assertIn("Gateway available", msg)

    def test_single_failure_increments_count_without_tripping(self):
        self.cred.record_failure("Portal HTTP 500 server error")
        self.cred.refresh_from_db()
        self.assertEqual(self.cred.consecutive_failures, 1)
        self.assertEqual(self.cred.circuit_state, 'closed')
        is_avail, _ = self.cred.is_available()
        self.assertTrue(is_avail)

    def test_reaching_failure_threshold_trips_circuit(self):
        self.cred.record_failure("Failure 1: Timeout")
        self.cred.record_failure("Failure 2: Gateway timeout")
        self.cred.record_failure("Failure 3: Bad gateway")
        self.cred.refresh_from_db()

        self.assertEqual(self.cred.consecutive_failures, 3)
        self.assertEqual(self.cred.circuit_state, 'open')
        self.assertIsNotNone(self.cred.tripped_until)
        self.assertIn("Circuit Tripped", self.cred.last_status)

        # Immediate check should show unavailable
        is_avail, msg = self.cred.is_available()
        self.assertFalse(is_avail)
        self.assertIn("circuit breaker tripped until", msg)

    def test_cooldown_expiry_transitions_to_half_open(self):
        self.cred.record_failure("Failure 1")
        self.cred.record_failure("Failure 2")
        self.cred.record_failure("Failure 3")
        self.cred.refresh_from_db()

        # Simulate time passage beyond cooldown
        self.cred.tripped_until = timezone.now() - timedelta(minutes=1)
        self.cred.save(update_fields=['tripped_until'])

        is_avail, msg = self.cred.is_available()
        self.assertTrue(is_avail)
        self.assertIn("half-open", msg)
        self.cred.refresh_from_db()
        self.assertEqual(self.cred.circuit_state, 'half_open')

    def test_success_resets_failures_and_closes_circuit(self):
        self.cred.record_failure("Failure 1")
        self.cred.record_failure("Failure 2")
        self.cred.record_success()
        self.cred.refresh_from_db()

        self.assertEqual(self.cred.consecutive_failures, 0)
        self.assertEqual(self.cred.circuit_state, 'closed')
        self.assertIsNone(self.cred.tripped_until)

    def test_admin_manual_reset(self):
        self.cred.circuit_state = 'open'
        self.cred.consecutive_failures = 5
        self.cred.tripped_until = timezone.now() + timedelta(minutes=20)
        self.cred.last_failure_reason = "Auth lockout"
        self.cred.save()

        self.cred.reset_circuit()
        self.cred.refresh_from_db()
        self.assertEqual(self.cred.circuit_state, 'closed')
        self.assertEqual(self.cred.consecutive_failures, 0)
        self.assertIsNone(self.cred.tripped_until)
        self.assertEqual(self.cred.last_failure_reason, '')

    def test_admin_action_reset_selected_circuits(self):
        self.cred.circuit_state = 'open'
        self.cred.consecutive_failures = 4
        self.cred.save()

        admin_instance = MedicalAidPortalCredentialAdmin(MedicalAidPortalCredential, AdminSite())
        request = Mock()
        request.user = self.user
        admin_instance.message_user = Mock()

        admin_instance.reset_selected_circuits(request, MedicalAidPortalCredential.objects.filter(pk=self.cred.pk))
        self.cred.refresh_from_db()
        self.assertEqual(self.cred.circuit_state, 'closed')
        self.assertEqual(self.cred.consecutive_failures, 0)


class CircuitBreakerRpaIntegrationTests(TestCase):
    def setUp(self):
        self.cred = MedicalAidPortalCredential.objects.create(
            administrator='discovery',
            username='BUR-DISC-MASTER',
            password='MasterPassword123',
            bureau_bhf_number='BUR-1002',
            is_active=True,
            circuit_state='open',
            consecutive_failures=3,
            tripped_until=timezone.now() + timedelta(minutes=15),
            last_failure_reason="Scheme portal maintenance window"
        )

        self.practice = Practice.objects.create(
            practice_name="Paediatric Care Centre",
            bhf_practice_number="1263250",
            hpcsa_number="0731757MP",
            owner_name="Dr. Dimakatso Letsie",
            phone="0115551234",
            fee_percentage=Decimal("2.00")
        )

        self.patient = Patient.objects.create(
            practice=self.practice,
            first_name="Neo",
            last_name="Molefe",
            id_number="2101015000082",
            date_of_birth=date(2021, 1, 1),
            gender="M"
        )

        self.scheme = PatientScheme.objects.create(
            patient=self.patient,
            scheme_name="Discovery Health Medical Scheme",
            membership_number="99887766",
            dependent_code="00"
        )

        self.claim = Claim.objects.create(
            practice=self.practice,
            patient=self.patient,
            patient_scheme=self.scheme,
            date_of_service=date(2026, 9, 10),
            claim_status='draft',
            total_billed=Decimal("650.00")
        )

        self.line = ClaimLineItem.objects.create(
            claim=self.claim,
            tariff_code="0190",
            icd10_primary="J06.9",
            amount_billed=Decimal("650.00")
        )

    def test_rpa_task_blocks_execution_when_circuit_tripped(self):
        res = submit_claim_rpa(self.claim.id)
        self.assertFalse(res['success'])
        self.assertEqual(res['reference_number'], 'CIRCUIT-OPEN')
        self.assertIn("circuit breaker tripped until", res['error'])

        # Confirm claim status remained draft and logged circuit reason
        self.claim.refresh_from_db()
        self.assertEqual(self.claim.claim_status, 'draft')
        self.assertIn("circuit breaker active", self.claim.notes)

        # Confirm RpaSubmissionLog created without running browser
        logs = RpaSubmissionLog.objects.filter(claim=self.claim)
        self.assertEqual(logs.count(), 1)
        self.assertFalse(logs.first().success)
        self.assertEqual(logs.first().reference_number, "CIRCUIT-OPEN")
