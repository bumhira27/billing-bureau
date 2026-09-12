from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from datetime import date
from practices.models import Practice
from patients.models import Patient
from reference_data.models import ICD10Code, TariffCode
from claims.models import Claim, ClaimLineItem
from claims.services.ai_extractor import ClinicalExtraction, ExtractedLineItem, ground_extraction, extract_from_image

class AIExtractorTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='password123')
        self.practice = Practice.objects.create(
            practice_name='Pretoria Health GP',
            bhf_practice_number='1234567',
            hpcsa_number='MP0123456',
            owner_name='Dr. Smith',
            phone='0123456789'
        )
        self.patient = Patient.objects.create(
            practice=self.practice,
            first_name='Sipho',
            last_name='Dlamini',
            id_number='8804155123088',
            date_of_birth=date(1988, 4, 15),
            gender='M'
        )
        self.icd = ICD10Code.objects.create(
            code='J06.9',
            description='Acute upper respiratory infection, unspecified',
            category='Respiratory',
            is_active=True
        )
        self.tariff = TariffCode.objects.create(
            code='0190',
            description='Consultation - established patient',
            default_amount=520.00,
            is_active=True
        )
        self.client = Client()
        self.client.login(username='tester', password='password123')

    def test_pydantic_schema_and_grounding(self):
        raw_extraction = ClinicalExtraction(
            patient_name='Sipho Dlamini',
            patient_id_or_dob='8804155123088',
            date_of_service='2026-03-12',
            clinical_notes='Acute cough and fever.',
            line_items=[
                ExtractedLineItem(
                    tariff_code='0190',
                    tariff_description='',
                    icd10_code='J06.9',
                    icd10_description='',
                    quantity=1,
                    billed_amount=0.0
                )
            ]
        )
        grounded = ground_extraction(raw_extraction)
        self.assertEqual(grounded.line_items[0].icd10_code, 'J06.9')
        self.assertEqual(grounded.line_items[0].icd10_description, 'Acute upper respiratory infection, unspecified')
        self.assertEqual(grounded.line_items[0].tariff_code, '0190')
        self.assertEqual(grounded.line_items[0].billed_amount, 520.00)

    def test_upload_note_view_get(self):
        response = self.client.get(reverse('claims:upload_note'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'AI Handwritten Note Capture')

    def test_upload_note_view_post_creates_draft(self):
        # Create 1x1 pixel GIF
        dummy_image = SimpleUploadedFile(
            name='test_note.jpg',
            content=b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;',
            content_type='image/jpeg'
        )
        response = self.client.post(reverse('claims:upload_note'), {
            'practice': self.practice.id,
            'note_file': dummy_image,
            'notes': 'Test doctor handwritten consult note'
        })
        # Should redirect to review screen
        self.assertEqual(response.status_code, 302)
        claim = Claim.objects.latest('id')
        self.assertEqual(claim.practice, self.practice)
        self.assertEqual(claim.source_type, 'photo')
        self.assertEqual(claim.claim_status, 'draft')
        self.assertTrue(claim.line_items.count() > 0)
        self.assertTrue(claim.total_billed > 0)

    def test_review_extracted_claim_view(self):
        claim = Claim.objects.create(
            practice=self.practice,
            patient=self.patient,
            source_type='photo',
            claim_status='draft',
            created_by=self.user,
            date_of_service=date.today()
        )
        line = ClaimLineItem.objects.create(
            claim=claim,
            tariff_code='0190',
            icd10_primary='J06.9',
            quantity=1,
            amount_billed=520.00
        )
        claim.recalculate_totals()

        response = self.client.get(reverse('claims:review_extracted', kwargs={'pk': claim.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Review Extracted Claim')
        self.assertContains(response, 'J06.9')
        self.assertContains(response, '520')
