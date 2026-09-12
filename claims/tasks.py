import os
import logging
from celery import shared_task
from django.utils import timezone
from django.core.files.base import ContentFile
from claims.models import Claim, RpaSubmissionLog, ClaimNote
from claims.scrubbing import ClaimScrubber
from credentials.models import MedicalAidPortalCredential

# Use the new modular RPA adapters
from rpa_adapters.discovery_bot import DiscoveryPortalBot
from rpa_adapters.medscheme_bot import MedschemePortalBot
from rpa_adapters.simulator_bot import SimulatorPortalBot
from rpa_adapters.dtos import ClaimDTO, PatientDTO, PracticeDTO, ClaimLineDTO

logger = logging.getLogger(__name__)

@shared_task
def submit_claim_rpa(claim_id: int):
    """
    Background Celery task that submits a claim directly to a medical scheme
    provider portal using the Bureau's master portal credentials, acting
    on behalf of the client practice and bypassing commercial switches.
    """
    try:
        claim = Claim.objects.select_related('practice', 'patient', 'patient_scheme').get(pk=claim_id)
    except Claim.DoesNotExist:
        logger.error(f"Claim with id {claim_id} does not exist.")
        return {"error": "Claim not found"}

    # 0. Pre-submission Scrubbing
    scrub_errors = ClaimScrubber.scrub(claim)
    if scrub_errors:
        claim.claim_status = 'requires_correction'
        error_msg = "\n".join(f"- {e}" for e in scrub_errors)
        note_text = f"Scrubbing Failed:\n{error_msg}"
        claim.notes = f"{claim.notes}\n\n{note_text}".strip() if claim.notes else note_text
        claim.save(update_fields=['claim_status', 'notes'])
        return {"success": False, "error": "Scrubbing failed", "details": scrub_errors}

    practice = claim.practice
    scheme_name = claim.patient_scheme.scheme_name if claim.patient_scheme else "Medical Scheme"
    
    # 1. Select the appropriate Bot and Bureau Master Credentials
    scheme_lower = scheme_name.lower()
    if 'discovery' in scheme_lower or 'la health' in scheme_lower or 'bankmed' in scheme_lower:
        admin_key = 'discovery'
        portal_name = "Discovery Health Bureau Portal"
        BotClass = DiscoveryPortalBot
    elif 'gems' in scheme_lower or 'bonitas' in scheme_lower or 'polmed' in scheme_lower or 'medscheme' in scheme_lower:
        admin_key = 'medscheme'
        portal_name = "Medscheme / GEMS Bureau Portal"
        BotClass = MedschemePortalBot
    elif 'momentum' in scheme_lower or 'metropolitan' in scheme_lower:
        admin_key = 'momentum'
        portal_name = "Momentum / Metropolitan Portal"
        BotClass = SimulatorPortalBot
    else:
        admin_key = 'simulator'
        portal_name = f"{scheme_name} Direct Bureau Gateway"
        BotClass = SimulatorPortalBot

    bureau_cred = MedicalAidPortalCredential.objects.filter(administrator=admin_key, is_active=True).first()
    if not bureau_cred:
        bureau_cred = MedicalAidPortalCredential.objects.filter(is_active=True).first()

    # Check Circuit Breaker before launching browser automation
    if bureau_cred:
        is_avail, avail_reason = bureau_cred.is_available()
        if not is_avail:
            logger.warning("Gateway %s circuit breaker is open: %s (claim %d)", portal_name, avail_reason, claim.id)
            RpaSubmissionLog.objects.create(
                claim=claim,
                portal_name=portal_name,
                success=False,
                reference_number="CIRCUIT-OPEN",
                message=f"Circuit Breaker tripped: {avail_reason}",
                execution_time_seconds=0.0
            )
            note_text = f"Gateway '{portal_name}' circuit breaker active: {avail_reason}"
            claim.notes = f"{claim.notes}\n\n{note_text}".strip() if claim.notes else note_text
            claim.save(update_fields=['notes'])
            return {
                "success": False,
                "reference_number": "CIRCUIT-OPEN",
                "portal": portal_name,
                "execution_time": 0.0,
                "error": avail_reason
            }

    username = bureau_cred.username if bureau_cred else "BUR-MASTER"
    password = bureau_cred.password if bureau_cred else "demo123"
    portal_url = bureau_cred.portal_url if bureau_cred else ""
    bot = BotClass(username=username, password=password, portal_url=portal_url, headless=True)

    # 2. Extract line item details and construct the standard ClaimDTO
    lines_dto = []
    for i, line in enumerate(claim.line_items.all()):
        lines_dto.append(ClaimLineDTO(
            line_number=i+1,
            tariff_code=line.tariff_code,
            icd10=line.icd10_primary,
            amount=float(line.amount_billed),
            modifiers=[]
        ))

    patient_dto = PatientDTO(
        full_name=claim.patient.full_name,
        id_number=claim.patient.id_number or "",
        membership_number=claim.patient_scheme.membership_number if claim.patient_scheme else "MEM9999",
        dependent_code=claim.patient_scheme.dependent_code if claim.patient_scheme else "00",
        scheme_name=scheme_name
    )

    practice_dto = PracticeDTO(
        practice_name=practice.practice_name,
        practice_number=practice.bhf_practice_number,
        provider_name=practice.owner_name
    )

    claim_dto = ClaimDTO(
        claim_id=claim.id,
        date_of_service=claim.date_of_service.strftime('%Y-%m-%d'),
        total_amount=float(claim.total_billed),
        patient=patient_dto,
        practice=practice_dto,
        lines=lines_dto,
        bureau_username=username,
        bureau_bhf=bureau_cred.bureau_bhf_number if bureau_cred else ''
    )

    # 3. Execute RPA Headless Browser automation via standardized interface
    try:
        result = bot.submit_claim(claim_dto)
        if result.success:
            if bureau_cred:
                bureau_cred.record_success()
        else:
            if bureau_cred:
                bureau_cred.record_failure(result.message)
    except Exception as exc:
        if bureau_cred:
            bureau_cred.record_failure(str(exc))
        raise

    # 4. Save audit log and visual screenshot proof
    log = RpaSubmissionLog(
        claim=claim,
        portal_name=portal_name,
        success=result.success,
        reference_number=result.reference_number,
        message=result.message,
        execution_time_seconds=result.execution_time
    )

    if result.screenshot_bytes:
        filename = f"claim_{claim.id}_ref_{result.reference_number}.png"
        log.screenshot.save(filename, ContentFile(result.screenshot_bytes), save=False)

    log.save()

    # 5. Update Claim record
    if result.success:
        claim.switch_reference_number = result.reference_number
        claim.claim_status = 'submitted'
        claim.submission_date = timezone.now().date()
        note_text = f"Direct Portal Submission (Bypassed Switch via Bureau RPA): Reference {result.reference_number} on {portal_name} (Bureau Login: {username}, Treating Practice: {practice.bhf_practice_number}). Time: {result.execution_time}s."
        claim.notes = f"{claim.notes}\n\n{note_text}".strip() if claim.notes else note_text
        claim.save()

    return {
        "success": result.success,
        "reference_number": result.reference_number,
        "portal": portal_name,
        "execution_time": result.execution_time
    }
