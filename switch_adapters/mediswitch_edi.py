from typing import List
from .dtos import ClaimDTO
import datetime

def generate_medclaim_edi(claims: List[ClaimDTO]) -> str:
    """
    Generates a standard Medclaim EDI flat file.
    
    Format (Simplified for demonstration):
    HDR|BUREAUNUM|DATETIME
    CLM|CLAIM_ID|PRACTICE_BHF|MEMBERSHIP_NUM|DEP_CODE|SCHEME|SERVICE_DATE|TOTAL_AMOUNT
    LIN|LINE_NUM|TARIFF|ICD10|AMOUNT
    FTR|TOTAL_CLAIMS|TOTAL_VALUE
    """
    lines = []
    now = datetime.datetime.now()
    
    # Header
    bureau_bhf = claims[0].bureau_bhf if claims else "000000"
    lines.append(f"HDR|{bureau_bhf}|{now.strftime('%Y%m%d%H%M%S')}")
    
    total_value = 0.0
    
    for claim in claims:
        # Claim Header
        lines.append(f"CLM|{claim.claim_id}|{claim.practice.practice_number}|{claim.patient.membership_number}|{claim.patient.dependent_code}|{claim.patient.scheme_name}|{claim.date_of_service.replace('-','')}|{claim.total_amount:.2f}")
        
        # Claim Lines
        for line in claim.lines:
            lines.append(f"LIN|{line.line_number}|{line.tariff_code}|{line.icd10}|{line.amount:.2f}")
            
        total_value += claim.total_amount
        
    # Footer
    lines.append(f"FTR|{len(claims)}|{total_value:.2f}")
    
    return "\n".join(lines)
