from celery import shared_task
import traceback
from .models import RemittanceFile, RemittanceLine
from .parsers.csv_parser import CSVRemittanceParser
from .parsers.xml_parser import XMLRemittanceParser
from .parsers.pipe_parser import PipeDelimitedParser
from .matching import AutoMatcher

@shared_task
def process_remittance_file(remittance_file_id):
    remittance_file = RemittanceFile.objects.get(id=remittance_file_id)
    remittance_file.processed_status = 'processing'
    remittance_file.save()

    try:
        content = remittance_file.file.read().decode('utf-8')
        ext = remittance_file.file.name.lower().split('.')[-1]
        
        parser = None
        if ext == 'csv':
            parser = CSVRemittanceParser(content)
        elif ext == 'xml':
            parser = XMLRemittanceParser(content)
        elif ext in ['txt', 'era']:
            parser = PipeDelimitedParser(content)
        else:
            raise ValueError("Unsupported file format")

        parsed_data = parser.parse()
        remittance_file.raw_content = {'data': parsed_data}
        remittance_file.total_records = len(parsed_data)
        remittance_file.save()

        for row in parsed_data:
            RemittanceLine.objects.create(
                remittance_file=remittance_file,
                practice_number=row.get('practice_number', ''),
                scheme_name=row.get('scheme_name', ''),
                membership_number=row.get('membership_number', ''),
                dependent_code=row.get('dependent_code', ''),
                patient_name=row.get('patient_name', ''),
                date_of_service=row.get('date_of_service'),
                tariff_code=row.get('tariff_code', ''),
                amount_claimed=row.get('amount_claimed', 0),
                amount_approved=row.get('amount_approved', 0),
                amount_paid=row.get('amount_paid', 0),
                reason_code=row.get('reason_code', ''),
                reason_description=row.get('reason_description', '')
            )

        matcher = AutoMatcher()
        matcher.match_remittance_file(remittance_file)

    except Exception as e:
        remittance_file.processed_status = 'error'
        remittance_file.error_log = traceback.format_exc()
        remittance_file.save()

import logging
from datetime import date, timedelta
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

@shared_task
def fetch_daily_remittances_task():
    """
    Scheduled task to automatically download eRA files via SFTP from BHF-accredited switches.
    This replaces the deprecated RPA portal scraping approach.
    """
    logger.info("Polling MediSwitch / Healthbridge SFTP mailboxes for incoming eRA files...")
    
    # SFTP logic would go here. For now, it's a stub to simulate finding a file.
    # In production, this pulls the XML/EDIFACT file directly from the switch clearinghouse.
    
    # Example:
    # files = sftp_client.list_era_files()
    # for file in files:
    #     content = sftp_client.download(file)
    #     remit_file = RemittanceFile.objects.create(...)
    #     process_remittance_file.delay(remit_file.id)
    pass

