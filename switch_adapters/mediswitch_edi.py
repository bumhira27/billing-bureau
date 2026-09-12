import datetime
from decimal import Decimal
from typing import List, Dict, Any, Tuple
from .dtos import ClaimDTO


def generate_medclaim_edi(claims: List[ClaimDTO], batch_number: str = "") -> str:
    """
    Generates a production-standard Medclaim EDI flat-file batch adhering to BHF
    (Board of Healthcare Funders) and South African clearinghouse specifications
    (MediSwitch / Healthbridge).

    Segment Structure:
    - HDR: Batch Header (Bureau BHF, Target Switch, Batch Ref, Creation Timestamp)
    - PRV: Treating Provider Segment (Practice BHF, Discipline, HPCSA, Provider Name)
    - PAT: Patient / Beneficiary (Scheme, Membership No, Dep Code, ID No, Surname, First Name, DOB, Gender)
    - CLM: Claim Encounter (Claim ID, Service Date, Auth No, Referring BHF, Claim Amount)
    - LIN: Treatment Line Item (Line No, Tariff, Qty, Primary ICD-10, Secondary ICD-10, Modifiers, Amount)
    - FTR: Batch Trailer (Claim Count, Total Line Count, Total Batch Monetary Value)
    """
    lines: List[str] = []
    now = datetime.datetime.now()
    batch_ref = batch_number or f"BAT{now.strftime('%Y%m%d%H%M%S')}"

    bureau_bhf = claims[0].bureau_bhf if claims and claims[0].bureau_bhf else "0000000"
    
    # 1. Batch Header (HDR)
    # Format: HDR|BUREAU_BHF|BATCH_REF|CREATION_TIMESTAMP|SWITCH_TARGET|FORMAT_VERSION
    lines.append(f"HDR|{bureau_bhf}|{batch_ref}|{now.strftime('%Y%m%d%H%M%S')}|MEDISWITCH|MEDCLAIM2.1")

    total_value = Decimal("0.00")
    total_lines = 0

    for claim in claims:
        # 2. Provider Record (PRV)
        # Format: PRV|PRACTICE_BHF|DISCIPLINE_CODE|HPCSA_NUMBER|PROVIDER_NAME
        lines.append(
            f"PRV|{claim.practice.practice_number}|{claim.practice.discipline_code}|"
            f"{claim.practice.hpcsa_number}|{claim.practice.provider_name.replace('|', '')}"
        )

        # 3. Patient & Beneficiary Record (PAT)
        # Format: PAT|SCHEME_NAME|MEMBERSHIP_NO|DEP_CODE|ID_NUMBER|SURNAME|FIRST_NAME|DOB|GENDER
        pat = claim.patient
        dob_str = pat.date_of_birth.replace("-", "") if pat.date_of_birth else ""
        lines.append(
            f"PAT|{pat.scheme_name.replace('|', '')}|{pat.membership_number}|{pat.dependent_code}|"
            f"{pat.id_number}|{pat.surname.replace('|', '')}|{pat.first_name.replace('|', '')}|"
            f"{dob_str}|{pat.gender}"
        )

        # 4. Claim Encounter Header (CLM)
        # Format: CLM|CLAIM_ID|SERVICE_DATE|AUTH_NUMBER|REFERRING_BHF|TOTAL_AMOUNT
        dos_clean = claim.date_of_service.replace("-", "")
        claim_amt = Decimal(str(claim.total_amount))
        lines.append(
            f"CLM|{claim.claim_id}|{dos_clean}|{claim.authorization_number}|"
            f"{claim.referring_doctor_bhf}|{claim_amt:.2f}"
        )

        # 5. Treatment Line Items (LIN)
        # Format: LIN|LINE_NO|TARIFF|QTY|ICD10_PRIMARY|ICD10_SECONDARY|MODIFIERS|AMOUNT|NAPPI
        for line in claim.lines:
            mod_str = ",".join(line.modifiers) if line.modifiers else ""
            line_amt = Decimal(str(line.amount))
            lines.append(
                f"LIN|{line.line_number}|{line.tariff_code}|{line.quantity}|{line.icd10}|"
                f"{line.icd10_secondary}|{mod_str}|{line_amt:.2f}|{line.nappi_code}"
            )
            total_lines += 1

        total_value += claim_amt

    # 6. Batch Trailer (FTR)
    # Format: FTR|BATCH_REF|TOTAL_CLAIMS|TOTAL_LINES|TOTAL_VALUE
    lines.append(f"FTR|{batch_ref}|{len(claims)}|{total_lines}|{total_value:.2f}")

    return "\n".join(lines)


def validate_medclaim_edi(edi_content: str) -> Tuple[bool, List[str]]:
    """
    Validates the structural integrity and checksum of a Medclaim EDI flat file.
    Returns (is_valid: bool, errors: List[str]).
    """
    errors = []
    lines = [line.strip() for line in edi_content.strip().split("\n") if line.strip()]

    if not lines:
        return False, ["EDI file is empty."]

    if not lines[0].startswith("HDR|"):
        errors.append("Missing HDR (Batch Header) segment as first line.")

    if not lines[-1].startswith("FTR|"):
        errors.append("Missing FTR (Batch Trailer) segment as final line.")

    if errors:
        return False, errors

    header_parts = lines[0].split("|")
    if len(header_parts) < 4:
        errors.append("Malformed HDR segment: insufficient header fields.")

    trailer_parts = lines[-1].split("|")
    if len(trailer_parts) < 5:
        errors.append("Malformed FTR segment: insufficient trailer fields.")
    else:
        try:
            expected_claims = int(trailer_parts[2])
            expected_lines = int(trailer_parts[3])
            expected_value = Decimal(trailer_parts[4])

            actual_claims = sum(1 for line in lines if line.startswith("CLM|"))
            actual_lines = sum(1 for line in lines if line.startswith("LIN|"))
            actual_value = Decimal("0.00")
            for line in lines:
                if line.startswith("CLM|"):
                    parts = line.split("|")
                    actual_value += Decimal(parts[5])

            if actual_claims != expected_claims:
                errors.append(f"Claim count mismatch: Header/Trailer states {expected_claims}, found {actual_claims}.")

            if actual_lines != expected_lines:
                errors.append(f"Line item count mismatch: Trailer states {expected_lines}, found {actual_lines}.")

            if abs(actual_value - expected_value) > Decimal("0.01"):
                errors.append(f"Monetary checksum mismatch: Trailer states R{expected_value}, actual total R{actual_value}.")
        except Exception as e:
            errors.append(f"Trailer verification failed: {e}")

    return len(errors) == 0, errors


def parse_clearinghouse_ack(ack_content: str) -> Dict[str, Any]:
    """
    Parses a Level 1 Switch Clearinghouse Acknowledgement (ACK/NAK) file.
    """
    lines = [line.strip() for line in ack_content.strip().split("\n") if line.strip()]
    result = {
        "status": "REJECTED",
        "batch_reference": "",
        "clearinghouse": "",
        "accepted_claims": 0,
        "rejected_claims": 0,
        "error_messages": []
    }

    for line in lines:
        parts = line.split("|")
        record_type = parts[0]

        if record_type == "ACK_HDR":
            result["batch_reference"] = parts[1] if len(parts) > 1 else ""
            result["clearinghouse"] = parts[2] if len(parts) > 2 else ""
            result["status"] = parts[3] if len(parts) > 3 else "ACCEPTED"
        elif record_type == "ACK_CLM":
            claim_status = parts[2] if len(parts) > 2 else "ACCEPTED"
            if claim_status == "ACCEPTED":
                result["accepted_claims"] += 1
            else:
                result["rejected_claims"] += 1
                if len(parts) > 3:
                    result["error_messages"].append(f"Claim {parts[1]}: {parts[3]}")
        elif record_type == "ACK_ERR":
            if len(parts) > 1:
                result["error_messages"].append(parts[1])

    return result
