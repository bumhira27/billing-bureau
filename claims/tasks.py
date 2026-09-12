import os
import logging
from datetime import datetime
from celery import shared_task
from django.utils import timezone
from django.core.files.base import ContentFile
from claims.models import Claim, RpaSubmissionLog
from claims.scrubbing import ClaimScrubber
from switch_adapters.dtos import ClaimDTO, PatientDTO, PracticeDTO, ClaimLineDTO
from switch_adapters.mediswitch_edi import generate_medclaim_edi

logger = logging.getLogger(__name__)

@shared_task
def batch_claims_edi():
    """
    Background Celery task that finds all claims in 'draft' or 'requires_correction' status,
    scrubs them, and generates a Medclaim EDI batch file for SFTP transmission to MediSwitch.
    """
    claims_to_submit = Claim.objects.filter(claim_status__in=['draft', 'submitted']).select_related('practice', 'patient', 'patient_scheme')
    
    if not claims_to_submit.exists():
        return {"success": True, "message": "No claims to batch"}
        
    valid_claims = []
    
    for claim in claims_to_submit:
        # 0. Pre-submission Scrubbing
        scrub_errors = ClaimScrubber.scrub(claim)
        if scrub_errors:
            claim.claim_status = 'requires_correction'
            error_msg = "\n".join(f"- {e}" for e in scrub_errors)
            note_text = f"Scrubbing Failed:\n{error_msg}"
            claim.notes = f"{claim.notes}\n\n{note_text}".strip() if claim.notes else note_text
            claim.save(update_fields=['claim_status', 'notes'])
            continue
            
        # 1. Extract line item details and construct the standard ClaimDTO
        lines_dto = []
        for i, line in enumerate(claim.line_items.all()):
            lines_dto.append(ClaimLineDTO(
                line_number=i+1,
                tariff_code=line.tariff_code,
                icd10=line.icd10_primary,
                amount=float(line.amount_billed),
                modifiers=[]
            ))
            
        scheme_name = claim.patient_scheme.scheme_name if claim.patient_scheme else "UNKNOWN"
            
        patient_dto = PatientDTO(
            full_name=claim.patient.full_name,
            id_number=claim.patient.id_number or "",
            membership_number=claim.patient_scheme.membership_number if claim.patient_scheme else "",
            dependent_code=claim.patient_scheme.dependent_code if claim.patient_scheme else "00",
            scheme_name=scheme_name
        )

        practice_dto = PracticeDTO(
            practice_name=claim.practice.practice_name,
            practice_number=claim.practice.bhf_practice_number,
            provider_name=claim.practice.owner_name
        )

        claim_dto = ClaimDTO(
            claim_id=claim.id,
            date_of_service=claim.date_of_service.strftime('%Y-%m-%d'),
            total_amount=float(claim.total_billed),
            patient=patient_dto,
            practice=practice_dto,
            lines=lines_dto,
            bureau_username="BUREAU",
            bureau_bhf="BUR999"
        )
        
        valid_claims.append((claim, claim_dto))

    if not valid_claims:
        return {"success": False, "message": "All claims failed scrubbing."}

    # 2. Generate EDI File
    dtos = [c[1] for c in valid_claims]
    edi_content = generate_medclaim_edi(dtos)
    batch_ref = f"BATCH-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # 3. Log Transmission
    for claim, dto in valid_claims:
        claim.claim_status = 'submitted'
        claim.submission_date = timezone.now().date()
        claim.switch_reference_number = batch_ref
        note_text = f"Claim batched for EDI transmission via MediSwitch. Batch Ref: {batch_ref}."
        claim.notes = f"{claim.notes}\n\n{note_text}".strip() if claim.notes else note_text
        claim.save()
        
        RpaSubmissionLog.objects.create(
            claim=claim,
            portal_name="MediSwitch EDI",
            success=True,
            reference_number=batch_ref,
            message="Batched into EDI file for SFTP drop",
            execution_time_seconds=0.0
        )
        
    return {
        "success": True,
        "batch_reference": batch_ref,
        "claims_batched": len(valid_claims)
    }
