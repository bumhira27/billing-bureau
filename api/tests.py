import json
import uuid
from decimal import Decimal
from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from practices.models import Practice
from patients.models import Patient, PatientScheme
from claims.models import Claim, ClaimLineItem
from api.models import IdempotencyRecord


class ApiV1ClaimsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.practice = Practice.objects.create(
            practice_name="Paediatric Excellence Centre",
            bhf_practice_number="1263250",
            hpcsa_number="0731757MP",
            owner_name="Dr. Dimakatso Letsie",
            phone="0115551234",
            fee_percentage=Decimal("2.00")
        )

        self.patient = Patient.objects.create(
            practice=self.practice,
            first_name="Sipho",
            last_name="Khumalo",
            id_number="1805125000089",
            date_of_birth=date(2018, 5, 12),
            gender="M"
        )

        self.scheme = PatientScheme.objects.create(
            patient=self.patient,
            scheme_name="Discovery Health Medical Scheme",
            scheme_option="Classic Comprehensive",
            membership_number="902288331",
            dependent_code="00"
        )

    def test_missing_idempotency_key_returns_rfc7807_error(self):
        url = reverse('api_v1:claim_create')
        payload = {
            "practice_number": "1263250",
            "patient_first_name": "Sipho",
            "patient_last_name": "Khumalo",
            "line_items": [{"tariff_code": "0190", "amount_billed": "550.00"}]
        }
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response['Content-Type'], 'application/problem+json')
        data = response.json()
        self.assertEqual(data['title'], "Missing Idempotency-Key")
        self.assertIn("Idempotency-Key", data['detail'])
        self.assertEqual(data['status'], 400)

    def test_claim_create_with_idempotency_and_replay(self):
        url = reverse('api_v1:claim_create')
        idem_key = str(uuid.uuid4())
        headers = {'HTTP_IDEMPOTENCY_KEY': idem_key}

        payload = {
            "practice_number": "1263250",
            "patient_id": self.patient.id,
            "scheme_name": "Discovery Health Medical Scheme",
            "membership_number": "902288331",
            "date_of_service": "2026-09-12",
            "line_items": [
                {
                    "tariff_code": "0190",
                    "tariff_description": "Paediatric Consultation",
                    "icd10_primary": "J06.9",
                    "quantity": 1,
                    "amount_billed": "650.00"
                }
            ]
        }

        # First request: Creates Claim
        initial_claim_count = Claim.objects.count()
        response1 = self.client.post(url, data=json.dumps(payload), content_type='application/json', **headers)
        self.assertEqual(response1.status_code, 201)
        data1 = response1.json()
        claim_id = data1['claim_id']
        self.assertEqual(Claim.objects.count(), initial_claim_count + 1)
        self.assertEqual(data1['total_billed'], "650.00")
        self.assertEqual(data1['status'], 'draft')

        # Verify idempotency record written
        record = IdempotencyRecord.objects.filter(idempotency_key=idem_key).first()
        self.assertIsNotNone(record)
        self.assertEqual(record.status_code, 201)

        # Second request: Network retry with same Idempotency-Key
        response2 = self.client.post(url, data=json.dumps(payload), content_type='application/json', **headers)
        self.assertEqual(response2.status_code, 201)
        self.assertEqual(response2.get('Idempotent-Replayed'), 'true')
        data2 = response2.json()
        self.assertEqual(data2['claim_id'], claim_id)
        # Verify no duplicate claim row was created
        self.assertEqual(Claim.objects.count(), initial_claim_count + 1)

    def test_claim_create_validation_errors(self):
        url = reverse('api_v1:claim_create')
        headers = {'HTTP_IDEMPOTENCY_KEY': str(uuid.uuid4())}

        # Missing practice number
        res1 = self.client.post(url, data=json.dumps({"patient_first_name": "Test"}), content_type='application/json', **headers)
        self.assertEqual(res1.status_code, 422)
        self.assertEqual(res1.json()['title'], "Missing Practice Number")

        # Unknown practice BHF
        headers2 = {'HTTP_IDEMPOTENCY_KEY': str(uuid.uuid4())}
        res2 = self.client.post(url, data=json.dumps({"practice_number": "0000000"}), content_type='application/json', **headers2)
        self.assertEqual(res2.status_code, 404)
        self.assertEqual(res2.json()['title'], "Practice Not Found")

        # Missing line items
        headers3 = {'HTTP_IDEMPOTENCY_KEY': str(uuid.uuid4())}
        res3 = self.client.post(url, data=json.dumps({"practice_number": "1263250", "line_items": []}), content_type='application/json', **headers3)
        self.assertEqual(res3.status_code, 422)
        self.assertEqual(res3.json()['title'], "Missing Line Items")

    def test_claim_detail_endpoint(self):
        claim = Claim.objects.create(
            practice=self.practice,
            patient=self.patient,
            patient_scheme=self.scheme,
            date_of_service=date(2026, 9, 11),
            claim_status='submitted',
            switch_reference_number='DIR-20260912-1001',
            total_billed=Decimal("800.00"),
            total_paid=Decimal("800.00")
        )
        ClaimLineItem.objects.create(
            claim=claim,
            tariff_code="0190",
            tariff_description="Consultation",
            icd10_primary="J06.9",
            amount_billed=Decimal("800.00"),
            amount_paid=Decimal("800.00"),
            line_status="paid"
        )

        url = reverse('api_v1:claim_detail', kwargs={'pk': claim.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['claim_id'], claim.id)
        self.assertEqual(data['switch_reference_number'], 'DIR-20260912-1001')
        self.assertEqual(data['practice']['bhf_number'], '1263250')
        self.assertEqual(len(data['line_items']), 1)
        self.assertEqual(data['line_items'][0]['line_status'], 'paid')

    def test_mobile_batch_sync_endpoint(self):
        url = reverse('api_v1:mobile_sync')
        batch_id = str(uuid.uuid4())
        headers = {'HTTP_IDEMPOTENCY_KEY': f"mobile-sync-{batch_id}"}

        payload = {
            "practice_number": "1263250",
            "batch_id": batch_id,
            "device_id": "dr-tablet-ward3-01",
            "encounters": [
                {
                    "client_encounter_id": "ward-round-01",
                    "patient_first_name": "Bokang",
                    "patient_last_name": "Mokoena",
                    "date_of_service": "2026-09-12",
                    "scheme_name": "Bonitas",
                    "membership_number": "33445566",
                    "tariff_code": "0101",
                    "icd10": "J18.9",
                    "amount": "450.00"
                },
                {
                    "client_encounter_id": "ward-round-02",
                    "patient_first_name": "Tshepo",
                    "patient_last_name": "Dlamini",
                    "date_of_service": "2026-09-12",
                    "scheme_name": "GEMS",
                    "membership_number": "77889900",
                    "tariff_code": "0101",
                    "icd10": "A09",
                    "amount": "450.00"
                }
            ]
        }

        response = self.client.post(url, data=json.dumps(payload), content_type='application/json', **headers)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['synced_count'], 2)
        self.assertEqual(len(data['claims']), 2)
        self.assertEqual(data['claims'][0]['client_encounter_id'], "ward-round-01")
        self.assertEqual(data['claims'][0]['total_billed'], "450.00")
