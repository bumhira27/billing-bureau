from decimal import Decimal
from datetime import date
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp import DEVICE_ID_SESSION_KEY

from practices.models import Practice
from patients.models import Patient, PatientScheme
from claims.models import Claim, ClaimLineItem, EdiTransmissionLog
from claims.tasks import batch_claims_edi


class EdiPipelineTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('editestadmin', 'edi@example.com', 'edipass123')
        StaticDevice.objects.create(user=self.user, name='test_device', confirmed=True)
        self.client = Client()
        self.client.force_login(self.user)
        session = self.client.session
        device = StaticDevice.objects.get(user=self.user)
        session[DEVICE_ID_SESSION_KEY] = device.persistent_id
        session.save()

        self.practice = Practice.objects.create(
            practice_name="Cape Paediatrics Practice",
            bhf_practice_number="0145555",
            hpcsa_number="MP0555555",
            owner_name="Dr. Sarah Johnson",
            phone="0215551234",
            switch_provider="mediswitch",
            switch_account_id="MSW-CP01"
        )
        self.patient = Patient.objects.create(
            practice=self.practice,
            first_name="Lethabo",
            last_name="Khuzwayo",
            id_number="2005055009081",
            date_of_birth=date(2020, 5, 5),
            gender="M"
        )
        self.scheme = PatientScheme.objects.create(
            patient=self.patient,
            scheme_name="Discovery Health Medical Scheme",
            membership_number="990011223",
            dependent_code="00"
        )
        self.claim = Claim.objects.create(
            practice=self.practice,
            patient=self.patient,
            patient_scheme=self.scheme,
            date_of_service=date(2026, 9, 10),
            total_billed=Decimal("650.00"),
            claim_status='draft',
            authorization_number="AUTH-9911"
        )
        self.line = ClaimLineItem.objects.create(
            claim=self.claim,
            tariff_code="0190",
            tariff_description="Consultation established patient",
            icd10_primary="J06.9",
            quantity=1,
            amount_billed=Decimal("650.00")
        )

    def test_batch_claims_edi_task_success(self):
        """Test background EDI batching, scrubbing verification, and log creation."""
        result = batch_claims_edi(claim_id=self.claim.id)
        self.assertTrue(result["success"])
        self.assertEqual(result["claims_batched"], 1)
        self.assertEqual(result["status"], "accepted")

        self.claim.refresh_from_db()
        self.assertEqual(self.claim.claim_status, "submitted")
        self.assertTrue(self.claim.switch_reference_number.startswith("MSW-"))

        # Verify EdiTransmissionLog
        log = EdiTransmissionLog.objects.filter(claim=self.claim).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.status, "accepted")
        self.assertEqual(log.switch_provider, "mediswitch")
        self.assertIn("HDR|BUR001|", log.edi_payload)
        self.assertIn("CLM|", log.edi_payload)
        self.assertIn("LIN|1|0190|1|J06.9|||650.00|", log.edi_payload)
        self.assertIn("FTR|", log.edi_payload)

    def test_claim_scrubbing_failure_blocks_edi_batch(self):
        """A claim with a clinical scrubbing error should fail before EDI transmission."""
        # Attach invalid gender diagnosis (O80 obstetric delivery on a male patient)
        self.line.icd10_primary = "O80"
        self.line.save()

        result = batch_claims_edi(claim_id=self.claim.id)
        self.assertFalse(result["success"])
        self.assertEqual(result["claims_batched"], 0)

        self.claim.refresh_from_db()
        self.assertEqual(self.claim.claim_status, "requires_correction")
        self.assertIn("Scrubbing Validation Failed", self.claim.notes)

        # Ensure no EDI transmission log was created for failed scrub
        self.assertFalse(EdiTransmissionLog.objects.filter(claim=self.claim).exists())

    def test_claim_edi_submit_view(self):
        """Test POST /claims/<id>/edi-submit/ triggers EDI batching."""
        url = reverse('claims:edi_submit', kwargs={'pk': self.claim.id})
        response = self.client.post(url)
        self.assertRedirects(response, reverse('claims:detail', kwargs={'pk': self.claim.id}))

        self.claim.refresh_from_db()
        self.assertEqual(self.claim.claim_status, "submitted")

    def test_edi_logs_list_view(self):
        """Test EDI transmission log audit view rendering."""
        batch_claims_edi(claim_id=self.claim.id)
        url = reverse('claims:edi_logs')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn("EDI Transmission Logs", content)
        self.assertIn("MSW-", content)
        self.assertIn("Accepted (ACK)", content)
