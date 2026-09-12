from django.test import TestCase
from switch_adapters.dtos import ClaimDTO, PatientDTO, PracticeDTO, ClaimLineDTO
from switch_adapters.mediswitch_edi import generate_medclaim_edi
import datetime

class EDITestCase(TestCase):
    def test_edi_generation(self):
        """Test that the EDI generator produces the correct flat-file format."""
        patient = PatientDTO(
            full_name="John Doe",
            id_number="9001015009087",
            membership_number="MEM123",
            dependent_code="00",
            scheme_name="Discovery"
        )
        practice = PracticeDTO(
            practice_name="Dr Smith",
            practice_number="PR123456",
            provider_name="Smith"
        )
        line = ClaimLineDTO(
            line_number=1,
            tariff_code="0190",
            icd10="J06.9",
            amount=550.00,
            modifiers=[]
        )
        claim = ClaimDTO(
            claim_id=1,
            date_of_service="2024-01-01",
            total_amount=550.00,
            patient=patient,
            practice=practice,
            lines=[line],
            bureau_username="TEST",
            bureau_bhf="BUR001"
        )
        
        edi_output = generate_medclaim_edi([claim])
        lines = edi_output.split("\n")
        
        self.assertTrue(lines[0].startswith("HDR|BUR001|"))
        self.assertEqual(lines[1], "CLM|1|PR123456|MEM123|00|Discovery|20240101|550.00")
        self.assertEqual(lines[2], "LIN|1|0190|J06.9|550.00")
        self.assertEqual(lines[3], "FTR|1|550.00")
