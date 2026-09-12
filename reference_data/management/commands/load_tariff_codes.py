import json
import os
from django.core.management.base import BaseCommand
from reference_data.models import TariffCode

class Command(BaseCommand):
    help = 'Loads Tariff codes from JSON fixture'

    def handle(self, *args, **options):
        fixture_path = os.path.join('reference_data', 'fixtures', 'tariff_codes.json')
        
        with open(fixture_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        created_count = 0
        skipped_count = 0
        
        for item in data:
            obj, created = TariffCode.objects.get_or_create(
                code=item['code'],
                defaults={
                    'description': item['description'],
                    'category': item['category'],
                    'default_amount': item.get('default_amount')
                }
            )
            if created:
                created_count += 1
            else:
                skipped_count += 1
                
        self.stdout.write(self.style.SUCCESS(f'Successfully loaded Tariff codes. Created: {created_count}, Skipped: {skipped_count}'))
