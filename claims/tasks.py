import logging
from datetime import datetime
from decimal import Decimal
from celery import shared_task
from django.utils import timezone
from claims.models import Claim, EdiTransmissionLog, RpaSubmissionLog
from claims.scrubbing import ClaimScrubber
from switch_adapters.dtos import ClaimDTO, PatientDTO, PracticeDTO, ClaimLineDTO
from switch_adapters.mediswitch_edi import generate_medclaim_edi
from switch_adapters.transport import SwitchTransport

logger = logging.getLogger(__name__)


@shared_task
def batch_claims_edi(claim_id=None):
    """
    Background Celery task that scrubs and compiles healthcare claims into a
    BHF-standard Medclaim EDI batch for clearinghouse transmission (MediSwitch / Healthbridge).

    If claim_id is provided, batches that single urgent claim immediately.
    Otherwise, aggregates all claims currently marked as 'draft' or 'submitted'.
    """
    if claim_id:
        claims_queryset = Claim.objects.filter(id=claim_id).select_related('practice', 'patient', 'patient_scheme')
    else:
        claims_queryset = Claim.objects.filter(claim_status__in=['draft', 'submitted']).select_related('practice', 'patient', 'patient_scheme')

    if not claims_queryset.exists():
        return {"success": True, "message": "No claims available for EDI batching.", "claims_batched": 0}

    valid_claims = []
    failed_scrubbing_count = 0

    for claim in claims_queryset:
        # 1. Pre-submission Clinical & Administrative Scrubbing
        scrub_errors = ClaimScrubber.scrub(claim)
        if scrub_errors:
            failed_scrubbing_count += 1
            claim.claim_status = 'requires_correction'
            error_msg = "\n".join(f"- {e}" for e in scrub_errors)
            note_text = f"Scrubbing Validation Failed:\n{error_msg}"
            claim.notes = f"{claim.notes}\n\n{note_text}".strip() if claim.notes else note_text
            claim.save(update_fields=['claim_status', 'notes'])
            continue

        # 2. Extract Line Items and build ClaimLineDTOs
        lines_dto = []
        for i, line in enumerate(claim.line_items.all()):
            lines_dto.append(ClaimLineDTO(
                line_number=i + 1,
                tariff_code=line.tariff_code,
                icd10=line.icd10_primary,
                amount=float(line.amount_billed),
                quantity=line.quantity,
                icd10_secondary=line.icd10_secondary,
                modifiers=line.modifier_codes or [],
                nappi_code=line.nappi_code
            ))

        scheme_name = claim.patient_scheme.scheme_name if claim.patient_scheme else "PRIVATE CASH"

        patient_dto = PatientDTO(
            full_name=claim.patient.full_name,
            surname=claim.patient.last_name,
            first_name=claim.patient.first_name,
            id_number=claim.patient.id_number or "",
            membership_number=claim.patient_scheme.membership_number if claim.patient_scheme else "",
            dependent_code=claim.patient_scheme.dependent_code if claim.patient_scheme else "00",
            scheme_name=scheme_name,
            date_of_birth=claim.patient.date_of_birth.strftime('%Y-%m-%d') if claim.patient.date_of_birth else "",
            gender=claim.patient.gender or "U"
        )

        practice_dto = PracticeDTO(
            practice_name=claim.practice.practice_name,
            practice_number=claim.practice.bhf_practice_number,
            provider_name=claim.practice.owner_name,
            hpcsa_number=claim.practice.hpcsa_number or "",
            discipline_code="014"
        )

        claim_dto = ClaimDTO(
            claim_id=claim.id,
            date_of_service=claim.date_of_service.strftime('%Y-%m-%d'),
            total_amount=float(claim.total_billed),
            patient=patient_dto,
            practice=practice_dto,
            lines=lines_dto,
            authorization_number=claim.authorization_number or "",
            referring_doctor_bhf=claim.referring_doctor_bhf or "",
            bureau_bhf="BUR001",
            bureau_username="BUREAU"
        )

        valid_claims.append((claim, claim_dto))

    if not valid_claims:
        return {
            "success": False,
            "message": f"All {failed_scrubbing_count} claim(s) failed pre-submission scrubbing.",
            "claims_batched": 0
        }

    # 3. Generate BHF Medclaim EDI Batch Flat-File
    timestamp_str = datetime.now().strftime('%Y%m%d%H%M%S')
    provider_name = valid_claims[0][0].practice.switch_provider or "mediswitch"
    if provider_name == 'none':
        provider_name = 'mediswitch'

    batch_ref = f"MSW-{timestamp_str}"
    dtos = [c[1] for c in valid_claims]
    edi_content = generate_medclaim_edi(dtos, batch_number=batch_ref)

    # 4. Transmit / Stage via SwitchTransport
    transmitted, raw_response, parsed_ack = SwitchTransport.transmit(
        batch_reference=batch_ref,
        content=edi_content,
        provider=provider_name,
        dry_run=True
    )

    batch_status = 'accepted' if (transmitted and parsed_ack.get('status') == 'ACCEPTED') else 'rejected'
    total_batch_value = sum(Decimal(str(c[0].total_billed)) for c in valid_claims)

    # 5. Log Transmission and Update Claim Records
    for claim, dto in valid_claims:
        claim.claim_status = 'submitted'
        claim.submission_date = timezone.now().date()
        claim.switch_reference_number = batch_ref
        note_text = f"Medclaim EDI Batch Generated: {batch_ref} via {provider_name.upper()}. Switch Status: {batch_status.upper()}."
        claim.notes = f"{claim.notes}\n\n{note_text}".strip() if claim.notes else note_text
        claim.save(update_fields=['claim_status', 'submission_date', 'switch_reference_number', 'notes'])

        EdiTransmissionLog.objects.create(
            claim=claim,
            batch_reference=batch_ref,
            switch_provider=provider_name,
            status=batch_status,
            edi_payload=edi_content,
            response_payload=raw_response,
            error_details="; ".join(parsed_ack.get('error_messages', [])),
            claims_count=len(valid_claims),
            total_amount=total_batch_value
        )

        # Retain backward compatibility for historical views
        RpaSubmissionLog.objects.create(
            claim=claim,
            portal_name=f"{provider_name.title()} EDI Switch",
            success=(batch_status == 'accepted'),
            reference_number=batch_ref,
            message=f"Transmitted in Medclaim EDI Batch {batch_ref}. Status: {batch_status.upper()}.",
            execution_time_seconds=0.05
        )

    logger.info(f"Successfully processed EDI batch {batch_ref} containing {len(valid_claims)} claim(s).")

    return {
        "success": True,
        "batch_reference": batch_ref,
        "claims_batched": len(valid_claims),
        "status": batch_status,
        "raw_response": raw_response
    }
