import datetime
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from practices.models import Practice
from patients.models import Patient
from claims.models import Claim, ClaimLineItem
from reconciliation.models import RemittanceLine
from .models import Payment, PatientStatement, BureauInvoice
from .tasks import generate_patient_statements_task, generate_bureau_invoices_task

class CollectionsAndInvoicingTests(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(
            practice_name="Test Practice",
            bhf_practice_number="123456",
            fee_percentage=Decimal("2.00")
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
        
    def test_bureau_invoice_generation(self):
        # Create a payment for last month
        last_month = datetime.date.today().replace(day=1) - datetime.timedelta(days=5)
        
        Payment.objects.create(
            claim=self.claim,
            payment_source='medical_scheme',
            amount=Decimal("800.00"),
            payment_date=last_month
        )
        
        # Run the task
        count = generate_bureau_invoices_task()
        self.assertEqual(count, 1)
        
        # Verify bureau invoice
        invoice = BureauInvoice.objects.first()
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.total_collections_processed, Decimal("800.00"))
        
        # 2% of 800 is 16.00
        self.assertEqual(invoice.invoice_total, Decimal("16.00"))
        
        # Verify invoice lines
        self.assertEqual(invoice.lines.count(), 1)
        line = invoice.lines.first()
        self.assertEqual(line.commission_fee, Decimal("16.00"))
