import datetime
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from practices.models import Practice
from patients.models import Patient
from claims.models import Claim, ClaimLineItem
from reconciliation.models import RemittanceLine
from .models import Payment, PatientStatement
from .tasks import generate_patient_statements_task

class CollectionsAndInvoicingTests(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(
            practice_name="Test Practice",
            bhf_practice_number="123456",

        )
        self.patient = Patient.objects.create(
            practice=self.practice,
            first_name="John",
            last_name="Doe",
            id_number="9001015000085",
            date_of_birth=datetime.date(1990, 1, 1),
            gender="M"
        )
        self.claim = Claim.objects.create(
            practice=self.practice,
            patient=self.patient,
            date_of_service=datetime.date(2026, 9, 1),
            claim_status='submitted',
            total_billed=Decimal("1000.00"),
            total_patient_liable=Decimal("200.00")  # Short-paid by R200
        )
        
    def test_patient_statement_generation(self):
        # Run the task
        count = generate_patient_statements_task()
        self.assertEqual(count, 1)
        
        # Verify statement created
        statement = PatientStatement.objects.first()
        self.assertIsNotNone(statement)
        self.assertEqual(statement.total_outstanding, Decimal("200.00"))
        self.assertIn("R200 is outstanding", statement.message_content)
        self.assertIn(self.claim, statement.claims_included.all())
        


