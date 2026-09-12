from decimal import Decimal
from django.test import TestCase
from switch_adapters.dtos import ClaimDTO, PatientDTO, PracticeDTO, ClaimLineDTO
from switch_adapters.mediswitch_edi import (
    generate_medclaim_edi,
    validate_medclaim_edi,
    parse_clearinghouse_ack
)
from switch_adapters.transport import SwitchTransport


class EDITestCase(TestCase):
    def setUp(self):
        self.patient = PatientDTO(
            full_name="John Doe",
            surname="Doe",
            first_name="John",
            id_number="9001015009087",
            membership_number="MEM123",
            dependent_code="00",
            scheme_name="Discovery Health",
            date_of_birth="1990-01-01",
            gender="M"
        )
        self.practice = PracticeDTO(
            practice_name="Dr Smith Paediatrics",
            practice_number="1234567",
            provider_name="Dr J Smith",
            hpcsa_number="MP0123456",
            discipline_code="014"
        )
        self.line = ClaimLineDTO(
            line_number=1,
            tariff_code="0190",
            icd10="J06.9",
            amount=550.00,
            quantity=1,
            modifiers=[]
        )
        self.claim = ClaimDTO(
            claim_id=101,
            date_of_service="2026-09-12",
            total_amount=550.00,
            patient=self.patient,
            practice=self.practice,
            lines=[self.line],
            authorization_number="AUTH9988",
            referring_doctor_bhf="0140001",
            bureau_bhf="BUR001"
        )

    def test_edi_generation_format(self):
        """Verify Medclaim EDI segments, delimiters, and monetary values."""
        edi_output = generate_medclaim_edi([self.claim], batch_number="BAT-TEST-001")
        lines = edi_output.split("\n")

        # HDR
        self.assertTrue(lines[0].startswith("HDR|BUR001|BAT-TEST-001|"))
        self.assertIn("MEDISWITCH|MEDCLAIM2.1", lines[0])

        # PRV
        self.assertEqual(lines[1], "PRV|1234567|014|MP0123456|Dr J Smith")

        # PAT
        self.assertEqual(lines[2], "PAT|Discovery Health|MEM123|00|9001015009087|Doe|John|19900101|M")

        # CLM
        self.assertEqual(lines[3], "CLM|101|20260912|AUTH9988|0140001|550.00")

        # LIN
        self.assertEqual(lines[4], "LIN|1|0190|1|J06.9|||550.00|")

        # FTR
        self.assertEqual(lines[5], "FTR|BAT-TEST-001|1|1|550.00")

    def test_edi_validation_success(self):
        """Verify structural validator passes on well-formed EDI batches."""
        edi_output = generate_medclaim_edi([self.claim], batch_number="BAT-VAL-001")
        is_valid, errors = validate_medclaim_edi(edi_output)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_edi_validation_checksum_failure(self):
        """Verify validator flags corrupted monetary or claim count totals."""
        corrupted_edi = "HDR|BUR001|BAT-VAL-001|20260912120000|MEDISWITCH|MEDCLAIM2.1\n" \
                        "CLM|101|20260912|||550.00\n" \
                        "LIN|1|0190|1|J06.9|||550.00|\n" \
                        "FTR|BAT-VAL-001|1|1|100.00"  # Stated R100, actual R550
        is_valid, errors = validate_medclaim_edi(corrupted_edi)
        self.assertFalse(is_valid)
        self.assertTrue(any("checksum mismatch" in e for e in errors))

    def test_transport_sandbox_transmission(self):
        """Verify transport staging and sandbox ACK loopback."""
        edi_output = generate_medclaim_edi([self.claim], batch_number="BAT-TR-001")
        success, raw_ack, parsed = SwitchTransport.transmit("BAT-TR-001", edi_output, dry_run=True)

        self.assertTrue(success)
        self.assertEqual(parsed["status"], "ACCEPTED")
        self.assertEqual(parsed["accepted_claims"], 1)
        self.assertIn("ACK_HDR|BAT-TR-001|MEDISWITCH|ACCEPTED", raw_ack)
