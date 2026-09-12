import os
import pandas as pd
import math
from django.core.management.base import BaseCommand
from reference_data.models import ICD10Code

class Command(BaseCommand):
    help = 'Loads ICD-10 Master Industry Table from an Excel file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the NDoH MIT Excel file')

    def handle(self, *args, **options):
        file_path = options['file_path']
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return

        self.stdout.write(f"Reading Excel file: {file_path}...")
        
        try:
            # The official NDoH file usually has the data on the first sheet or a sheet named 'SA ICD-10 MIT*'
            xl = pd.ExcelFile(file_path)
            sheet_name = xl.sheet_names[0]
            for s in xl.sheet_names:
                if 'MIT' in s.upper():
                    sheet_name = s
                    break
            
            self.stdout.write(f"Loading data from sheet '{sheet_name}'...")
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            # Basic validation
            required_cols = ['ICD10_Code', 'WHO_Full_Desc', 'Chapter_Desc', 'Valid_ICD10_ClinicalUse']
            for col in required_cols:
                if col not in df.columns:
                    self.stdout.write(self.style.ERROR(f'Missing required column: {col}'))
                    return
            
            # Clean up dataframe
            df = df.dropna(subset=['ICD10_Code'])
            
            # We'll do a bulk create/update for speed
            codes_to_create = []
            codes_to_update = []
            
            # Fetch existing to avoid IntegrityError and determine if update or create
            existing_codes = {c.code: c for c in ICD10Code.objects.all()}
            
            total = len(df)
            self.stdout.write(f"Processing {total} rows...")
            
            for index, row in df.iterrows():
                code_val = str(row['ICD10_Code']).strip()
                desc_val = str(row['WHO_Full_Desc']).strip()
                cat_val = str(row['Chapter_Desc']).strip()
                
                # Check for nan
                if pd.isna(row['WHO_Full_Desc']): desc_val = ""
                if pd.isna(row['Chapter_Desc']): cat_val = "Uncategorized"
                
                # NDoH 'Valid_ICD10_ClinicalUse' is 'Y' or 'N'
                is_active = str(row['Valid_ICD10_ClinicalUse']).strip().upper() == 'Y'
                
                if code_val in existing_codes:
                    obj = existing_codes[code_val]
                    # Update if changed
                    if obj.description != desc_val or obj.category != cat_val or obj.is_active != is_active:
                        obj.description = desc_val[:500]
                        obj.category = cat_val[:255]
                        obj.is_active = is_active
                        codes_to_update.append(obj)
                else:
                    obj = ICD10Code(
                        code=code_val[:10],
                        description=desc_val[:500],
                        category=cat_val[:255],
                        is_active=is_active
                    )
                    codes_to_create.append(obj)
                    # Add to existing to handle duplicates in the excel file itself
                    existing_codes[code_val] = obj

                if index > 0 and index % 2000 == 0:
                    self.stdout.write(f"Processed {index}/{total}...")

            if codes_to_create:
                self.stdout.write(f"Bulk creating {len(codes_to_create)} new codes...")
                ICD10Code.objects.bulk_create(codes_to_create, batch_size=1000)
            
            if codes_to_update:
                self.stdout.write(f"Bulk updating {len(codes_to_update)} existing codes...")
                ICD10Code.objects.bulk_update(codes_to_update, ['description', 'category', 'is_active'], batch_size=1000)

            self.stdout.write(self.style.SUCCESS(f'Successfully loaded MIT data. Created: {len(codes_to_create)}, Updated: {len(codes_to_update)}'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error processing file: {e}'))
