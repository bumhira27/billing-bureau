from .base import BaseRemittanceParser
from decimal import Decimal

class PipeDelimitedParser(BaseRemittanceParser):
    def parse(self) -> list[dict]:
        lines = self.file_content.splitlines()
        results = []
        
        current_provider = None
        current_scheme = None
        current_member = None
        current_patient = None
        current_treatment = None
        
        for line in lines:
            if not line.strip():
                continue
            parts = line.split('|')
            record_type = parts[0]
            
            if record_type == 'S':
                current_provider = parts[1] if len(parts) > 1 else ''
            elif record_type == 'M':
                current_scheme = parts[1] if len(parts) > 1 else ''
                current_member = parts[2] if len(parts) > 2 else ''
            elif record_type == 'P':
                current_patient = parts[2] if len(parts) > 2 else ''
                # dependent code usually around parts[3] or similar, keeping generic
            elif record_type == 'T':
                current_treatment = {
                    'practice_number': current_provider,
                    'scheme_name': current_scheme,
                    'membership_number': current_member,
                    'patient_name': current_patient,
                    'date_of_service': parts[1] if len(parts) > 1 else None,
                    'tariff_code': parts[2] if len(parts) > 2 else None,
                    'amount_claimed': Decimal(parts[3]) / 100 if len(parts) > 3 and parts[3] else Decimal(0)
                }
            elif record_type == 'Z':
                if current_treatment:
                    current_treatment['amount_approved'] = Decimal(parts[1]) / 100 if len(parts) > 1 and parts[1] else Decimal(0)
                    current_treatment['amount_paid'] = Decimal(parts[2]) / 100 if len(parts) > 2 and parts[2] else Decimal(0)
                    results.append(self.validate_row(current_treatment))
                    # Note: we might need to link R records if they follow
            elif record_type == 'R':
                if results:
                    last_record = results[-1]
                    last_record['reason_code'] = parts[1] if len(parts) > 1 else ''
                    last_record['reason_description'] = parts[2] if len(parts) > 2 else ''
        return results
