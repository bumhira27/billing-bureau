import os
from decimal import Decimal
from datetime import date
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from practices.models import Practice, PortalCredential
from credentials.models import MedicalAidPortalCredential
from patients.models import Patient, PatientScheme
from claims.models import Claim, ClaimLineItem, RpaSubmissionLog
from claims.rpa.simulator_bot import SimulatorPortalBot
from claims.rpa.discovery_bot import DiscoveryPortalBot
from claims.rpa.medscheme_bot import MedschemePortalBot
from claims.tasks import submit_claim_rpa


class RpaPortalBotTests(TestCase):
    def test_simulator_bot_headless_execution(self):
        bot = SimulatorPortalBot(username="BUR-DH-88921", password="testpassword", headless=True)
        self.assertTrue(bot.verify_login())

        claim_data = {
            'patient_name': 'Test Baby Patient',
            'membership_number': '901234567',
            'dependent_code': '00',
            'tariff_code': '0190',
            'icd10': 'J06.9',
            'amount_billed': '550.00',
            'practice_number': '1263250',
            'practice_name': 'Rising Star Paediatrics',
            'doctor_name': 'Dr. Dimakatso Letsie',
            'bureau_username': 'BUR-DH-88921',
            'bureau_bhf': 'BUR-88921',
            'scheme_name': 'Discovery Health Medical Scheme',
            'date_of_service': '2026-09-12'
        }

        result = bot.submit_claim(claim_data)
        self.assertTrue(result.success)
        self.assertTrue(result.reference_number.startswith("DIR-"))
        self.assertIsNotNone(result.screenshot_bytes)
        self.assertGreater(len(result.screenshot_bytes), 1000)
        self.assertGreater(result.execution_time, 0.0)

    def test_discovery_bot_delegation(self):
        bot = DiscoveryPortalBot(username="BUR-DH-88921", password="testpassword", headless=True)
        self.assertTrue(bot.verify_login())
        claim_data = {
            'patient_name': 'Discovery Patient',
            'membership_number': '987654321',
            'amount_billed': '620.00',
            'bureau_username': 'BUR-DH-88921',
            'practice_number': '1263250'
        }
        res = bot.submit_claim(claim_data)
        self.assertTrue(res.success)
        self.assertTrue(res.reference_number.startswith("DIR-"))
        self.assertEqual(res.portal_name, "Discovery Health Medical Scheme")


class RpaTaskAndWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('testadmin', 'admin@example.com', 'pass123')
        self.client = Client()
        self.client.force_login(self.user)

        # Central Bureau Master Credential
        self.bureau_cred = MedicalAidPortalCredential.objects.create(
            administrator='discovery',
            username='BUR-DH-88921',
            password='BureauSecurePassword2026',
            bureau_bhf_number='BUR-88921',
            is_active=True
        )

        self.practice = Practice.objects.create(
            practice_name="Rising Star Paediatrics (Pty) Ltd",
            bhf_practice_number="1263250",
            hpcsa_number="0731757MP",
            owner_name="Dr. Dimakatso Tsholofetso Letsie",
            phone="0115551234",
            email="specialist@example.com",
            fee_percentage=Decimal("2.00")
        )

        self.cred_discovery = PortalCredential.objects.create(
            practice=self.practice,
            administrator='discovery',
            username='1263250',
            password='VaultPassword123',
            is_active=True
        )

        self.patient = Patient.objects.create(
            practice=self.practice,
            first_name="Liam",
            last_name="Zulu",
            id_number="2005015000081",
            date_of_birth=date(2020, 5, 1),
            gender="M"
        )

        self.scheme = PatientScheme.objects.create(
            patient=self.patient,
            scheme_name="Discovery Health Medical Scheme",
            scheme_option="Classic Priority",
            membership_number="902233445",
            dependent_code="01",
            is_active=True
        )

        self.claim = Claim.objects.create(
            practice=self.practice,
            patient=self.patient,
            patient_scheme=self.scheme,
            date_of_service=date(2026, 9, 10),
            claim_status='draft',
            total_billed=Decimal("550.00")
        )

        self.line_item = ClaimLineItem.objects.create(
            claim=self.claim,
            tariff_code="0190",
            tariff_description="Consultation GP",
            icd10_primary="J06.9",
            amount_billed=Decimal("550.00")
        )

    def test_submit_claim_rpa_celery_task(self):
        res = submit_claim_rpa(self.claim.id)
        self.assertTrue(res['success'])
        self.assertTrue(res['reference_number'].startswith("DIR-"))

        self.claim.refresh_from_db()
        self.assertEqual(self.claim.claim_status, 'submitted')
        self.assertEqual(self.claim.switch_reference_number, res['reference_number'])
        self.assertEqual(self.claim.rpa_submissions.count(), 1)

        log = self.claim.rpa_submissions.first()
        self.assertTrue(log.success)
        self.assertEqual(log.reference_number, res['reference_number'])
        self.assertTrue(bool(log.screenshot))
        self.assertTrue(os.path.exists(log.screenshot.path))
        self.assertGreater(log.execution_time_seconds, Decimal("0.00"))

    def test_portal_credential_test_view(self):
        url = reverse('practices:credential_test', kwargs={'pk': self.cred_discovery.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        self.cred_discovery.refresh_from_db()
        self.assertIsNotNone(self.cred_discovery.last_tested)

    def test_claim_rpa_submit_endpoint(self):
        url = reverse('claims:rpa_submit', kwargs={'pk': self.claim.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        self.claim.refresh_from_db()
        self.assertEqual(self.claim.claim_status, 'submitted')
        self.assertTrue(self.claim.switch_reference_number.startswith("DIR-"))

    def test_bureau_credential_admin_action(self):
        from credentials.admin import MedicalAidPortalCredentialAdmin
        from django.contrib.admin.sites import AdminSite
        from unittest.mock import Mock
        admin_instance = MedicalAidPortalCredentialAdmin(MedicalAidPortalCredential, AdminSite())
        request = Mock()
        request.user = self.user
        admin_instance.message_user = Mock()
        admin_instance.test_selected_credentials(request, MedicalAidPortalCredential.objects.filter(pk=self.bureau_cred.pk))
        self.bureau_cred.refresh_from_db()
        self.assertEqual(self.bureau_cred.last_status, "Authentication Verified")
        self.assertIsNotNone(self.bureau_cred.last_tested)
