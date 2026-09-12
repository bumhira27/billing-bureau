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
from credentials.models import MedicalAidPortalCredential
from rpa_adapters.discovery_bot import DiscoveryPortalBot
from rpa_adapters.medscheme_bot import MedschemePortalBot

logger = logging.getLogger(__name__)

@shared_task
def fetch_daily_remittances_task():
    """
    Scheduled task to automatically download eRA files from all active portals
    for the previous day, and save them as RemittanceFile records.
    """
    credentials = MedicalAidPortalCredential.objects.filter(is_active=True)
    
    # By default, fetch for yesterday
    yesterday = date.today() - timedelta(days=1)
    date_str = yesterday.strftime('%Y-%m-%d')
    
    for cred in credentials:
        if cred.administrator == 'discovery':
            bot = DiscoveryPortalBot(username=cred.username, password=cred.password, portal_url=cred.portal_url, headless=True)
        elif cred.administrator == 'medscheme':
            bot = MedschemePortalBot(username=cred.username, password=cred.password, portal_url=cred.portal_url, headless=True)
        else:
            continue
            
        try:
            logger.info(f"Fetching remittances for {cred.administrator} ({cred.username}) for {date_str}")
            # Fetch files
            file_bytes_list = bot.fetch_remittances(date_str, date_str)
            
            for idx, file_bytes in enumerate(file_bytes_list):
                # Create RemittanceFile
                remit_file = RemittanceFile(
                    switch_provider=cred.administrator,
                    file_name=f"{cred.administrator}_era_{date_str}_{idx}.txt",
                    total_records=0,
                    total_amount=0.00,
                    processed_status='pending'
                )
                remit_file.file.save(f"{cred.administrator}_{date_str}_{idx}.txt", ContentFile(file_bytes))
                remit_file.save()
                
                logger.info(f"Saved RemittanceFile {remit_file.id} for {cred.administrator}")
                
                # Trigger AutoMatcher automatically
                process_remittance_file.delay(remit_file.id)
                
        except Exception as e:
            logger.error(f"Failed to fetch remittances for {cred.administrator} ({cred.username}): {str(e)}")
