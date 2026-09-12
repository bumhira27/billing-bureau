from dataclasses import dataclass
from typing import List, Type
from claims.models import Claim

@dataclass
class RuleResult:
    passed: bool
    error_message: str = ""

class BaseScrubbingRule:
    """Base class for all scrubbing rules."""
    @classmethod
    def run(cls, claim: Claim) -> RuleResult:
        raise NotImplementedError

class GenderDiagnosisMatchRule(BaseScrubbingRule):
    """Checks if gender-specific ICD-10 codes match the patient's sex."""
    MALE_ONLY_PREFIXES = ('N40', 'N41', 'N42', 'N43', 'N44', 'N45', 'N46', 'N47', 'N48', 'N49', 'N50', 'N51')
    FEMALE_ONLY_PREFIXES = ('N7', 'N8', 'N9', 'O0', 'O1', 'O2', 'O3', 'O4', 'O5', 'O6', 'O7', 'O8', 'O9')

    @classmethod
    def run(cls, claim: Claim) -> RuleResult:
        if not claim.patient or not claim.patient.gender:
            return RuleResult(True)  # Can't validate if gender missing
        
        gender = claim.patient.gender.lower()
        for line in claim.line_items.all():
            icd10 = line.icd10_primary.upper() if line.icd10_primary else ""
            if gender == 'male' and any(icd10.startswith(prefix) for prefix in cls.FEMALE_ONLY_PREFIXES):
                return RuleResult(False, f"Diagnosis {icd10} on line {line.id} is invalid for male patient.")
            if gender == 'female' and any(icd10.startswith(prefix) for prefix in cls.MALE_ONLY_PREFIXES):
                return RuleResult(False, f"Diagnosis {icd10} on line {line.id} is invalid for female patient.")
        return RuleResult(True)

class AgeTariffMatchRule(BaseScrubbingRule):
    """Validates pediatric or geriatric specific tariff codes."""
    PEDIATRIC_TARIFFS = ('0190', '0191', '0192')
    
    @classmethod
    def run(cls, claim: Claim) -> RuleResult:
        if not claim.patient or not claim.patient.date_of_birth:
            return RuleResult(True)
            
        age_days = (claim.date_of_service - claim.patient.date_of_birth).days
        age_years = age_days / 365.25
        
        for line in claim.line_items.all():
            if line.tariff_code in cls.PEDIATRIC_TARIFFS and age_years > 18:
                return RuleResult(False, f"Tariff code {line.tariff_code} on line {line.id} is pediatric only (Patient is {int(age_years)} years old).")
        return RuleResult(True)

class ClaimScrubber:
    """Registry of rules to scrub a claim."""
    _rules: List[Type[BaseScrubbingRule]] = [
        GenderDiagnosisMatchRule,
        AgeTariffMatchRule
    ]

    @classmethod
    def scrub(cls, claim: Claim) -> List[str]:
        """Runs all rules and returns a list of error messages. Empty list means passed."""
        errors = []
        for rule_class in cls._rules:
            result = rule_class.run(claim)
            if not result.passed:
                errors.append(result.error_message)
        return errors
