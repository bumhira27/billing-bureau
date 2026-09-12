from django.test import TestCase
from datetime import date
from claims.models import Claim, ClaimLineItem
from patients.models import Patient
from practices.models import Practice
from claims.scrubbing import ClaimScrubber

class ScrubbingRulesTestCase(TestCase):
    def setUp(self):
        self.practice = Practice.objects.create(
            practice_name="Test Practice",
            bhf_practice_number="PR123"
        )
        # Create an adult male patient
        self.male_patient = Patient.objects.create(
            practice=self.practice,
            first_name="John",
            last_name="Doe",
            gender="M",
            date_of_birth=date(1980, 1, 1), # 46 years old
            id_number="8001015000080"
        )
        # Create a pediatric female patient
        self.child_patient = Patient.objects.create(
            practice=self.practice,
            first_name="Jane",
            last_name="Doe",
            gender="F",
            date_of_birth=date(2020, 1, 1), # 6 years old
            id_number="2001015000080"
        )
        
    def test_gender_mismatch_rule_male(self):
        claim = Claim.objects.create(
            practice=self.practice,
            patient=self.male_patient,
            date_of_service=date(2026, 9, 12),
            claim_status='draft'
        )
        # Add a female-only ICD10 code (e.g. O80 - single spontaneous delivery)
        ClaimLineItem.objects.create(claim=claim, tariff_code="0201", icd10_primary="O80", amount_billed=100)
        
        errors = ClaimScrubber.scrub(claim)
        self.assertEqual(len(errors), 1)
        self.assertIn("invalid for male patient", errors[0])

    def test_pediatric_tariff_on_adult(self):
        claim = Claim.objects.create(
            practice=self.practice,
            patient=self.male_patient, # Adult
            date_of_service=date(2026, 9, 12),
            claim_status='draft'
        )
        # Add a pediatric tariff code 
        ClaimLineItem.objects.create(claim=claim, tariff_code="0192", icd10_primary="J06.9", amount_billed=100)
        
        errors = ClaimScrubber.scrub(claim)
        self.assertEqual(len(errors), 1)
        self.assertIn("is pediatric only", errors[0])
        
    def test_valid_pediatric_claim(self):
        claim = Claim.objects.create(
            practice=self.practice,
            patient=self.child_patient, # Child
            date_of_service=date(2026, 9, 12),
            claim_status='draft'
        )
        ClaimLineItem.objects.create(claim=claim, tariff_code="0192", icd10_primary="J06.9", amount_billed=100)
        
        errors = ClaimScrubber.scrub(claim)
        self.assertEqual(len(errors), 0) # Should pass
