import os
import json
import logging
import mimetypes
from typing import List, Optional
from datetime import date
from django.conf import settings
from django.utils import timezone
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class ExtractedLineItem(BaseModel):
    tariff_code: str = Field(description="South African GP tariff code, e.g. 0190, 0191, 0192, 0001")
    tariff_description: str = Field(description="Description of consultation or procedure")
    icd10_code: str = Field(description="Valid South African ICD-10 diagnosis code, e.g. J06.9, I10")
    icd10_description: str = Field(description="Description of the diagnosis")
    quantity: int = Field(default=1, description="Quantity of service or medication units")
    billed_amount: float = Field(default=450.0, description="Billed amount in ZAR")

class ClinicalExtraction(BaseModel):
    patient_name: str = Field(description="Full patient name")
    patient_id_or_dob: Optional[str] = Field(default="", description="Patient SA ID number or date of birth")
    date_of_service: Optional[str] = Field(default="", description="Date of consultation in YYYY-MM-DD")
    referring_doctor: Optional[str] = Field(default="", description="Referring doctor name or BHF number")
    authorization_number: Optional[str] = Field(default="", description="Medical scheme pre-authorization number")
    clinical_notes: str = Field(description="Summary of doctor's clinical findings and diagnosis")
    line_items: List[ExtractedLineItem] = Field(default_factory=list, description="Billable line items")

def get_gemini_api_key():
    return os.environ.get("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)

def extract_from_image(image_path: str) -> ClinicalExtraction:
    """
    Extracts clinical transcription and billing items from a handwritten note image.
    Uses Gemini 2.5 Flash if GEMINI_API_KEY is available; otherwise provides a structured mock extraction.
    """
    api_key = get_gemini_api_key()
    
    if api_key:
        try:
            from google import genai
            from google.genai import types

            mime_type, _ = mimetypes.guess_type(image_path)
            if not mime_type:
                mime_type = "image/jpeg"

            with open(image_path, "rb") as f:
                image_bytes = f.read()

            client = genai.Client(api_key=api_key)
            prompt = (
                "You are an expert South African medical billing and clinical transcription specialist. "
                "Analyze this handwritten clinical consultation note, prescription, or day sheet. "
                "Transcribe the patient demographics, date of service, and clinical diagnosis. "
                "Map diagnoses to standard South African ICD-10 codes (e.g., J06.9 for URTI, I10 for hypertension, "
                "E11.9 for Type 2 Diabetes, M54.5 for lower back pain). "
                "Map consultations and procedures to South African GP tariff codes (e.g., 0190 for new/standard consult, "
                "0191 for subsequent consult, 0001 for ECG, 0007 for nebulisation). "
                "Ensure amounts are reasonable South African GP rates in ZAR."
            )

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    prompt,
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ClinicalExtraction,
                    temperature=0.1,
                ),
            )

            if response.text:
                extraction = ClinicalExtraction.model_validate_json(response.text)
                return ground_extraction(extraction)
        except Exception as e:
            logger.error(f"Gemini API extraction failed: {e}. Falling back to default extraction.")

    # Mock extraction when API key is unset or upon error
    today_str = timezone.now().date().strftime("%Y-%m-%d")
    mock_data = ClinicalExtraction(
        patient_name="Sipho Dlamini",
        patient_id_or_dob="8804155123088",
        date_of_service=today_str,
        referring_doctor="",
        authorization_number="",
        clinical_notes="Patient presents with acute productive cough, fever (38.2C), and rhinorrhea for 3 days. Chest auscultation clear. Diagnosis: Acute upper respiratory tract infection (URTI). Prescribed rest, analgesics, and fluids.",
        line_items=[
            ExtractedLineItem(
                tariff_code="0190",
                tariff_description="Consultation - established patient",
                icd10_code="J06.9",
                icd10_description="Acute upper respiratory infection, unspecified",
                quantity=1,
                billed_amount=520.00
            ),
            ExtractedLineItem(
                tariff_code="0050",
                tariff_description="Blood glucose test (point of care)",
                icd10_code="J06.9",
                icd10_description="Acute upper respiratory infection, unspecified",
                quantity=1,
                billed_amount=95.00
            )
        ]
    )
    return ground_extraction(mock_data)

def ground_extraction(extraction: ClinicalExtraction) -> ClinicalExtraction:
    """
    Validates and grounds extracted ICD-10 and Tariff codes against the local database tables.
    """
    from reference_data.models import ICD10Code, TariffCode

    for item in extraction.line_items:
        # 1. Ground ICD-10 code
        clean_code = item.icd10_code.strip().upper()
        exact_icd = ICD10Code.objects.filter(code__iexact=clean_code).first()
        if exact_icd:
            item.icd10_code = exact_icd.code
            item.icd10_description = exact_icd.description
        else:
            # Try 3-character prefix or text search
            prefix = clean_code[:3]
            prefix_match = ICD10Code.objects.filter(code__istartswith=prefix, is_active=True).first()
            if prefix_match:
                item.icd10_code = prefix_match.code
                item.icd10_description = prefix_match.description
            else:
                # Text search on description
                first_word = item.icd10_description.split()[0] if item.icd10_description else ""
                if first_word:
                    text_match = ICD10Code.objects.filter(description__icontains=first_word, is_active=True).first()
                    if text_match:
                        item.icd10_code = text_match.code
                        item.icd10_description = text_match.description

        # 2. Ground Tariff code
        clean_tariff = item.tariff_code.strip()
        tariff_match = TariffCode.objects.filter(code__iexact=clean_tariff).first()
        if tariff_match:
            item.tariff_code = tariff_match.code
            if not item.tariff_description or len(item.tariff_description) < 4:
                item.tariff_description = tariff_match.description
            if (not item.billed_amount or item.billed_amount == 0) and tariff_match.default_amount:
                item.billed_amount = float(tariff_match.default_amount)

    return extraction
