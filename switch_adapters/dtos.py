from dataclasses import dataclass, asdict
from typing import List, Optional

@dataclass
class PatientDTO:
    full_name: str
    id_number: str
    membership_number: str
    dependent_code: str
    scheme_name: str

@dataclass
class PracticeDTO:
    practice_name: str
    practice_number: str
    provider_name: str

@dataclass
class ClaimLineDTO:
    line_number: int
    tariff_code: str
    icd10: str
    amount: float
    modifiers: List[str]

@dataclass
class ClaimDTO:
    """
    A standardized Data Transfer Object representing a Claim, loosely inspired by 
    the HL7 FHIR Claim resource. This insulates our RPA bots from the Django ORM.
    """
    claim_id: int
    date_of_service: str
    total_amount: float
    patient: PatientDTO
    practice: PracticeDTO
    lines: List[ClaimLineDTO]
    
    bureau_username: str = ""
    bureau_bhf: str = ""

    def to_dict(self):
        return asdict(self)
