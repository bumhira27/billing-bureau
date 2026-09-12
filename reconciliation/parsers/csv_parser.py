import csv
import io
from .base import BaseRemittanceParser

class CSVRemittanceParser(BaseRemittanceParser):
    COLUMN_MAP = {
        'practice no': 'practice_number',
        'practicenumber': 'practice_number',
        'practice_number': 'practice_number',
        'scheme': 'scheme_name',
        'scheme_name': 'scheme_name',
        'member no': 'membership_number',
        'membership_number': 'membership_number',
        'member number': 'membership_number',
        'dep': 'dependent_code',
        'dependent': 'dependent_code',
        'dependent_code': 'dependent_code',
        'patient': 'patient_name',
        'patient_name': 'patient_name',
        'date': 'date_of_service',
        'date_of_service': 'date_of_service',
        'tariff': 'tariff_code',
        'tariff_code': 'tariff_code',
        'claimed': 'amount_claimed',
        'amount_claimed': 'amount_claimed',
        'approved': 'amount_approved',
        'amount_approved': 'amount_approved',
        'paid': 'amount_paid',
        'amount_paid': 'amount_paid',
        'reason': 'reason_code',
        'reason_code': 'reason_code',
        'description': 'reason_description',
        'reason_description': 'reason_description'
    }

    def parse(self) -> list[dict]:
        reader = csv.reader(io.StringIO(self.file_content))
        rows = list(reader)
        if not rows:
            return []

        header = [h.strip() for h in rows[0]]
        results = []

        # Detect GoodX format
        if 'Debtor Name' in header and 'Invoice Nr' in header:
            # GoodX ERA export layout
            for row in rows[1:]:
                if not row or len(row) < 11:
                    continue
                debtor_name = row[1].strip() if len(row) > 1 else ''
                debtor_nr = row[2].strip() if len(row) > 2 else ''
                inv_nr = row[6].strip() if len(row) > 6 else ''
                inv_date = row[7].strip() if len(row) > 7 else ''
                tariff = row[8].strip() if len(row) > 8 else ''
                desc = row[9].strip() if len(row) > 9 else ''
                alloc_amount = row[10].strip() if len(row) > 10 else '0.0'
                ma_msg = row[17].strip() if len(row) > 17 else ''

                reason_code = ''
                reason_desc = ma_msg
                if '-' in ma_msg:
                    parts = ma_msg.split('-', 1)
                    if parts[0].strip().isdigit():
                        reason_code = parts[0].strip()
                        reason_desc = parts[1].strip()

                norm_row = {
                    'practice_number': '1263250',
                    'scheme_name': '',
                    'membership_number': debtor_nr,
                    'dependent_code': '00',
                    'patient_name': debtor_name,
                    'date_of_service': inv_date,
                    'tariff_code': tariff,
                    'amount_claimed': alloc_amount,
                    'amount_approved': alloc_amount,
                    'amount_paid': alloc_amount,
                    'reason_code': reason_code,
                    'reason_description': reason_desc,
                    'invoice_nr': inv_nr
                }
                results.append(self.validate_row(norm_row))
        else:
            # Standard dictionary reader format
            dict_reader = csv.DictReader(io.StringIO(self.file_content))
            for row in dict_reader:
                normalized_row = {}
                for k, v in row.items():
                    if not k: continue
                    norm_k = k.lower().strip()
                    if norm_k in self.COLUMN_MAP:
                        normalized_row[self.COLUMN_MAP[norm_k]] = v
                results.append(self.validate_row(normalized_row))

        return results

