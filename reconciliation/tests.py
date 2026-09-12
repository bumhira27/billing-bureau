from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from practices.models import Practice
from patients.models import Patient, PatientScheme
from claims.models import Claim, ClaimLineItem
from reconciliation.models import RemittanceFile, RemittanceLine, ReconciliationLog
from reconciliation.matching import AutoMatcher


class AutoMatcherTransactionalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('adminrec', 'rec@example.com', 'pass123')
        self.client = Client()
        self.client.force_login(self.user)

        self.practice = Practice.objects.create(
            practice_name="Paediatric Care",
            bhf_practice_number="1263250",
            hpcsa_number="0731757MP",
            owner_name="Dr. Dimakatso Letsie",
            phone="0115551234",
            fee_percentage=Decimal("2.00")
        )

        self.patient = Patient.objects.create(
            practice=self.practice,
            first_name="Kagiso",
            last_name="Modise",
            id_number="2201015000085",
            date_of_birth=date(2022, 1, 1),
            gender="M"
        )

        self.scheme = PatientScheme.objects.create(
            patient=self.patient,
            scheme_name="Discovery Health Medical Scheme",
            membership_number="99881122",
            dependent_code="00"
        )

        self.claim = Claim.objects.create(
            practice=self.practice,
            patient=self.patient,
            patient_scheme=self.scheme,
            date_of_service=date(2026, 9, 10),
            claim_status='submitted',
            total_billed=Decimal("1000.00")
        )

        self.line1 = ClaimLineItem.objects.create(
            claim=self.claim,
            tariff_code="0190",
            tariff_description="Consultation",
            icd10_primary="J06.9",
            quantity=1,
            amount_billed=Decimal("600.00")
        )

        self.line2 = ClaimLineItem.objects.create(
            claim=self.claim,
            tariff_code="0007",
            tariff_description="Nebulisation",
            icd10_primary="J06.9",
            quantity=1,
            amount_billed=Decimal("400.00")
        )

        self.remittance_file = RemittanceFile.objects.create(
            file_name="DH_ERA_20260912.txt",
            switch_provider="mediswitch",
            total_records=2,
            total_amount=Decimal("950.00"),
            processed_status="pending"
        )

    def test_auto_matcher_exact_and_short_paid(self):
        # Line 1: Paid in full (R600.00)
        remit_line1 = RemittanceLine.objects.create(
            remittance_file=self.remittance_file,
            practice_number="1263250",
            scheme_name="Discovery Health Medical Scheme",
            membership_number="99881122",
            dependent_code="00",
            patient_name="Modise K",
            date_of_service=date(2026, 9, 10),
            tariff_code="0190",
            amount_claimed=Decimal("600.00"),
            amount_approved=Decimal("600.00"),
            amount_paid=Decimal("600.00")
        )

        # Line 2: Short paid (R350.00 out of R400.00) with rejection code 12
        remit_line2 = RemittanceLine.objects.create(
            remittance_file=self.remittance_file,
            practice_number="1263250",
            scheme_name="Discovery Health Medical Scheme",
            membership_number="99881122",
            dependent_code="00",
            patient_name="Modise K",
            date_of_service=date(2026, 9, 10),
            tariff_code="0007",
            amount_claimed=Decimal("400.00"),
            amount_approved=Decimal("350.00"),
            amount_paid=Decimal("350.00"),
            reason_code="12",
            reason_description="Amount exceeds scheme rate"
        )

        matcher = AutoMatcher()
        summary = matcher.match_remittance_file(self.remittance_file)

        self.assertEqual(summary['matched'], 2)
        self.assertEqual(summary['unmatched'], 0)

        # Verify Line 1 updates
        self.line1.refresh_from_db()
        self.assertEqual(self.line1.line_status, 'paid')
        self.assertEqual(self.line1.amount_paid, Decimal("600.00"))
        self.assertEqual(self.line1.amount_patient_liable, Decimal("0.00"))

        # Verify Line 2 updates (short paid)
        self.line2.refresh_from_db()
        self.assertEqual(self.line2.line_status, 'short_paid')
        self.assertEqual(self.line2.amount_paid, Decimal("350.00"))
        self.assertEqual(self.line2.amount_patient_liable, Decimal("50.00"))
        self.assertEqual(self.line2.rejection_code, "12")

        # Verify Claim totals recalculation
        self.claim.refresh_from_db()
        self.assertEqual(self.claim.total_paid, Decimal("950.00"))
        self.assertEqual(self.claim.total_patient_liable, Decimal("50.00"))
        self.assertEqual(self.claim.claim_status, 'partially_paid')

        # Verify RemittanceFile counters
        self.remittance_file.refresh_from_db()
        self.assertEqual(self.remittance_file.records_matched, 2)
        self.assertEqual(self.remittance_file.processed_status, 'completed')

    def test_manual_match_view_atomic_execution(self):
        unmatched_line = RemittanceLine.objects.create(
            remittance_file=self.remittance_file,
            practice_number="1263250",
            membership_number="DIFFERENT-NUM",
            date_of_service=date(2026, 9, 10),
            tariff_code="0190",
            amount_claimed=Decimal("600.00"),
            amount_paid=Decimal("600.00"),
            match_status='unmatched'
        )

        url = reverse('reconciliation:manual_match')
        post_data = {
            'remittance_line_id': unmatched_line.id,
            'claim_line_item_id': self.line1.id,
            'notes': 'Matched manually by senior bureau supervisor'
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        unmatched_line.refresh_from_db()
        self.assertEqual(unmatched_line.match_status, 'manual_matched')
        self.assertEqual(unmatched_line.matched_claim_line_item, self.line1)

        self.line1.refresh_from_db()
        self.assertEqual(self.line1.line_status, 'paid')
        self.assertEqual(self.line1.amount_paid, Decimal("600.00"))

        log = ReconciliationLog.objects.filter(remittance_line=unmatched_line).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.match_method, 'manual')
        self.assertEqual(log.matched_by, self.user)
