from dataclasses import dataclass, asdict, field
from typing import List, Optional


@dataclass
class PatientDTO:
    full_name: str
    id_number: str
    membership_number: str
    dependent_code: str
    scheme_name: str
    date_of_birth: str = ""
    gender: str = ""
    surname: str = ""
    first_name: str = ""


@dataclass
class PracticeDTO:
    practice_name: str
    practice_number: str  # 7-digit BHF practice number
    provider_name: str
    hpcsa_number: str = ""
    discipline_code: str = "014"  # Default General Medical Practitioner


@dataclass
class ClaimLineDTO:
    line_number: int
    tariff_code: str
    icd10: str
    amount: float
    modifiers: List[str] = field(default_factory=list)
    quantity: int = 1
    icd10_secondary: str = ""
    nappi_code: str = ""


@dataclass
class ClaimDTO:
    """
    Standardized Data Transfer Object representing a healthcare claim for Medclaim
    EDI switch transmission to BHF-accredited clearinghouses (MediSwitch, Healthbridge).
    """
    claim_id: int
    date_of_service: str
    total_amount: float
    patient: PatientDTO
    practice: PracticeDTO
    lines: List[ClaimLineDTO]
    authorization_number: str = ""
    referring_doctor_bhf: str = ""
    bureau_username: str = ""
    bureau_bhf: str = ""

    def to_dict(self):
        return asdict(self)
