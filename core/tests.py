from django.test import TestCase, Client
from django.template import Template, Context
from django.contrib.auth.models import User
from decimal import Decimal
from core.templatetags.currency_tags import rands, percentage
from practices.models import Practice
from patients.models import Patient
from claims.models import Claim, ClaimLineItem
from billing_collections.models import Payment, PatientStatement
from datetime import date
from django_otp.plugins.otp_static.models import StaticDevice


class CurrencyTagsFilterTest(TestCase):
    def test_rands_filter_various_types(self):
        self.assertEqual(rands(1234.56), "R 1,234.56")
        self.assertEqual(rands(Decimal('7628.90')), "R 7,628.90")
        self.assertEqual(rands(1000), "R 1,000.00")
        self.assertEqual(rands(0), "R 0.00")
        self.assertEqual(rands(None), "R 0.00")
        self.assertEqual(rands(""), "R 0.00")
        self.assertEqual(rands("2617.8000000000"), "R 2,617.80")
        self.assertEqual(rands("R 5,011.10"), "R 5,011.10")
        self.assertEqual(rands(-450.50), "-R 450.50")

    def test_percentage_filter(self):
        self.assertEqual(percentage(65.7123), "65.7%")
        self.assertEqual(percentage(20), "20.0%")
        self.assertEqual(percentage(Decimal('100.0')), "100.0%")
        self.assertEqual(percentage(None), "0.0%")
        self.assertEqual(percentage(""), "0.0%")
        self.assertEqual(percentage("15.5%"), "15.5%")

    def test_builtins_in_templates(self):
        # Template without explicit {% load currency_tags %}
        template_code = "{{ amount|rands }} | {{ rate|percentage }}"
        tpl = Template(template_code)
        rendered = tpl.render(Context({'amount': 7628.9000000, 'rate': 65.73}))
        self.assertEqual(rendered, "R 7,628.90 | 65.7%")


class SiteWideCurrencyRenderingTest(TestCase):
    def setUp(self):
        self.client = Client(SERVER_NAME='127.0.0.1')
        self.user = User.objects.create_superuser('testadmin', 'test@example.com', 'adminpass123')
        # Create a confirmed OTP device so the user passes MFA checks
        StaticDevice.objects.create(user=self.user, name='test', confirmed=True)
        self.client.login(username='testadmin', password='adminpass123')
        # Mark session as OTP-verified
        session = self.client.session
        from django_otp import DEVICE_ID_SESSION_KEY
        device = StaticDevice.objects.get(user=self.user)
        session[DEVICE_ID_SESSION_KEY] = device.persistent_id
        session.save()

        self.practice = Practice.objects.create(
            practice_name="Test Paediatrics",
            bhf_practice_number="9990001",
            hpcsa_number="MP9999",
            owner_name="Dr Test",
            phone="0115551234",
            fee_percentage=Decimal('2.00')
        )
        self.patient = Patient.objects.create(
            practice=self.practice,
            first_name="John",
            last_name="Doe",
            id_number="9001015009087",
            date_of_birth=date(1990, 1, 1),
            gender="M"
        )
        self.claim = Claim.objects.create(
            practice=self.practice,
            patient=self.patient,
            date_of_service=date(2026, 9, 1),
            total_billed=Decimal('7628.90'),
            total_paid=Decimal('5011.10'),
            total_patient_liable=Decimal('2617.80'),
            claim_status='partially_paid'
        )
        self.line_item = ClaimLineItem.objects.create(
            claim=self.claim,
            tariff_code="0190",
            icd10_primary="J06.9",
            amount_billed=Decimal('7628.90'),
            amount_paid=Decimal('5011.10'),
            amount_patient_liable=Decimal('2617.80'),
            line_status='short_paid'
        )
        self.payment = Payment.objects.create(
            claim=self.claim,
            claim_line_item=self.line_item,
            payment_source='medical_scheme',
            amount=Decimal('5011.10'),
            payment_date=date(2026, 9, 5)
        )
        self.statement = PatientStatement.objects.create(
            patient=self.patient,
            practice=self.practice,
            total_outstanding=Decimal('2617.80'),
            delivery_status='sent'
        )

    def test_collections_overview_rendering(self):
        response = self.client.get('/collections/')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn("R 2,617.80", content)
        self.assertIn("R 5,011.10", content)
        # Ensure raw float unformatted values are absent
        self.assertNotIn("2617.800000", content)
        self.assertNotIn("5011.100000", content)

    def test_collections_statement_list_rendering(self):
        response = self.client.get('/collections/statements/')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn("R 2,617.80", content)

    def test_collections_payment_list_rendering(self):
        response = self.client.get('/collections/payments/')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn("R 5,011.10", content)

    def test_practice_detail_rendering(self):
        response = self.client.get(f'/practices/{self.practice.id}/')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn("R 7,628.90", content)
        self.assertIn("R 5,011.10", content)
        self.assertIn("R 2,617.80", content)
        self.assertNotIn("7628.900000", content)

    def test_patient_detail_rendering(self):
        response = self.client.get(f'/patients/{self.patient.id}/')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn("R 2,617.80", content)
        self.assertIn("R 7,628.90", content)
