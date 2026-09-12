import abc
from datetime import datetime
from decimal import Decimal
import decimal

class BaseRemittanceParser(abc.ABC):
    def __init__(self, file_content: str):
        self.file_content = file_content

    @abc.abstractmethod
    def parse(self) -> list[dict]:
        pass

    def validate_row(self, row: dict) -> dict:
        # Convert amounts to Decimal
        for field in ['amount_claimed', 'amount_approved', 'amount_paid']:
            if field in row:
                try:
                    row[field] = Decimal(str(row[field]))
                except (ValueError, TypeError, decimal.InvalidOperation):
                    row[field] = Decimal('0.00')

        # Parse date if it's a string
        if 'date_of_service' in row and isinstance(row['date_of_service'], str):
            try:
                # Attempt common formats
                for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y%m%d'):
                    try:
                        row['date_of_service'] = datetime.strptime(row['date_of_service'], fmt).date()
                        break
                    except ValueError:
                        pass
            except Exception:
                pass
        return row
