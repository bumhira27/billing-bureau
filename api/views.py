import json
from decimal import Decimal
from datetime import datetime, date
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.db import transaction
from django.shortcuts import get_object_or_404

from practices.models import Practice
from patients.models import Patient, PatientScheme
from claims.models import Claim, ClaimLineItem
from .decorators import idempotent_endpoint
from .utils import problem_details


@csrf_exempt
@require_http_methods(["POST"])
@idempotent_endpoint(scope='claims_create')
def claim_create_api(request):
    """
    POST /api/v1/claims/
    Create a new claim with line items for a practice.
    Enforces Idempotency-Key to prevent duplicate medical scheme claims.
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
    except (ValueError, json.JSONDecodeError):
        return problem_details(
            status=400,
            title="Invalid JSON",
            detail="The request body must be valid JSON.",
            instance=request.path
        )

    # Validate required fields
    practice_number = body.get('practice_number')
    if not practice_number:
        return problem_details(
            status=422,
            title="Missing Practice Number",
            detail="Field 'practice_number' (BHF number) is required.",
            instance=request.path
        )

    practice = Practice.objects.filter(bhf_practice_number=str(practice_number).strip()).first()
    if not practice:
        return problem_details(
            status=404,
            title="Practice Not Found",
            detail=f"No practice found with BHF number '{practice_number}'.",
            instance=request.path
        )

    patient_id = body.get('patient_id')
    patient = None
    if patient_id:
        patient = Patient.objects.filter(id=patient_id, practice=practice).first()

    if not patient:
        first_name = body.get('patient_first_name') or "Unknown"
        last_name = body.get('patient_last_name') or "Patient"
        dob_str = body.get('patient_dob')
        try:
            dob = datetime.strptime(dob_str, '%Y-%m-%d').date() if dob_str else date(1980, 1, 1)
        except ValueError:
            dob = date(1980, 1, 1)

        patient, _ = Patient.objects.get_or_create(
            practice=practice,
            first_name=first_name,
            last_name=last_name,
            defaults={
                'id_number': body.get('patient_id_number', ''),
                'date_of_birth': dob,
                'gender': body.get('patient_gender', 'O'),
                'phone': body.get('patient_phone', ''),
            }
        )

    # Optional Scheme Info
    scheme_name = body.get('scheme_name')
    membership_number = body.get('membership_number')
    patient_scheme = None
    if scheme_name and membership_number:
        patient_scheme, _ = PatientScheme.objects.get_or_create(
            patient=patient,
            membership_number=str(membership_number).strip(),
            defaults={
                'scheme_name': scheme_name,
                'scheme_option': body.get('scheme_option', ''),
                'dependent_code': body.get('dependent_code', '00'),
                'is_active': True
            }
        )

    # Date of service
    dos_str = body.get('date_of_service')
    try:
        date_of_service = datetime.strptime(dos_str, '%Y-%m-%d').date() if dos_str else date.today()
    except ValueError:
        return problem_details(
            status=422,
            title="Invalid Date Format",
            detail="Field 'date_of_service' must be formatted as YYYY-MM-DD.",
            instance=request.path
        )

    line_items_data = body.get('line_items', [])
    if not line_items_data:
        return problem_details(
            status=422,
            title="Missing Line Items",
            detail="At least one line item is required to create a claim.",
            instance=request.path
        )

    with transaction.atomic():
        claim = Claim.objects.create(
            practice=practice,
            patient=patient,
            patient_scheme=patient_scheme,
            date_of_service=date_of_service,
            referring_doctor_bhf=body.get('referring_doctor_bhf', ''),
            referring_doctor_name=body.get('referring_doctor_name', ''),
            authorization_number=body.get('authorization_number', ''),
            source_type='manual',
            notes=body.get('notes', 'Submitted via REST API v1')
        )

        total_billed = Decimal('0.00')
        for item in line_items_data:
            tariff = str(item.get('tariff_code', '0190')).strip()
            icd10 = str(item.get('icd10_primary', 'J06.9')).strip().upper()
            qty = int(item.get('quantity', 1))
            raw_amount = item.get('amount_billed', '0.00')
            try:
                amount = Decimal(str(raw_amount))
            except Exception:
                amount = Decimal('0.00')

            ClaimLineItem.objects.create(
                claim=claim,
                tariff_code=tariff,
                tariff_description=item.get('tariff_description', ''),
                icd10_primary=icd10,
                icd10_secondary=item.get('icd10_secondary', ''),
                quantity=qty,
                amount_billed=amount,
                nappi_code=item.get('nappi_code', '')
            )
            total_billed += amount

        claim.recalculate_totals()

    response_data = {
        "claim_id": claim.id,
        "status": claim.claim_status,
        "practice_number": practice.bhf_practice_number,
        "practice_name": practice.practice_name,
        "patient_name": patient.full_name,
        "date_of_service": claim.date_of_service.strftime('%Y-%m-%d'),
        "total_billed": f"{claim.total_billed:.2f}",
        "line_items_count": claim.line_items.count()
    }
    return JsonResponse(response_data, status=201)


@require_http_methods(["GET"])
def claim_detail_api(request, pk):
    """
    GET /api/v1/claims/<id>/
    Retrieve claim details, financial status, and line items.
    """
    claim = get_object_or_404(Claim.objects.select_related('practice', 'patient', 'patient_scheme'), pk=pk)
    
    lines = []
    for item in claim.line_items.all():
        lines.append({
            "id": item.id,
            "tariff_code": item.tariff_code,
            "description": item.tariff_description,
            "icd10_primary": item.icd10_primary,
            "quantity": item.quantity,
            "amount_billed": f"{item.amount_billed:.2f}",
            "amount_paid": f"{item.amount_paid:.2f}",
            "amount_patient_liable": f"{item.amount_patient_liable:.2f}",
            "line_status": item.line_status,
            "rejection_code": item.rejection_code or None
        })

    data = {
        "claim_id": claim.id,
        "status": claim.claim_status,
        "practice": {
            "name": claim.practice.practice_name,
            "bhf_number": claim.practice.bhf_practice_number
        },
        "patient": {
            "name": claim.patient.full_name,
            "id_number": claim.patient.id_number,
            "scheme": claim.patient_scheme.scheme_name if claim.patient_scheme else None,
            "membership_number": claim.patient_scheme.membership_number if claim.patient_scheme else None
        },
        "date_of_service": claim.date_of_service.strftime('%Y-%m-%d'),
        "switch_reference_number": claim.switch_reference_number or None,
        "total_billed": f"{claim.total_billed:.2f}",
        "total_paid": f"{claim.total_paid:.2f}",
        "outstanding_balance": f"{claim.outstanding_balance:.2f}",
        "line_items": lines
    }
    return JsonResponse(data, status=200)


@csrf_exempt
@require_http_methods(["POST"])
@idempotent_endpoint(scope='mobile_sync')
def mobile_batch_sync_api(request):
    """
    POST /api/v1/mobile/sync/
    Doctor offline bedside batch sync endpoint.
    Accepts encounters recorded while disconnected and creates draft claims atomically.
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
    except (ValueError, json.JSONDecodeError):
        return problem_details(
            status=400,
            title="Invalid JSON",
            detail="The request body must be valid JSON.",
            instance=request.path
        )

    practice_number = body.get('practice_number')
    practice = Practice.objects.filter(bhf_practice_number=str(practice_number).strip()).first()
    if not practice:
        return problem_details(
            status=404,
            title="Practice Not Found",
            detail=f"Practice BHF '{practice_number}' not found.",
            instance=request.path
        )

    encounters = body.get('encounters', [])
    if not isinstance(encounters, list):
        return problem_details(
            status=422,
            title="Invalid Encounters Array",
            detail="Field 'encounters' must be a JSON array of clinical encounters.",
            instance=request.path
        )

    created_claims = []
    with transaction.atomic():
        for enc in encounters:
            patient_name = enc.get('patient_name', 'Walk-in Patient').strip()
            name_parts = patient_name.split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else 'Patient'

            patient, _ = Patient.objects.get_or_create(
                practice=practice,
                first_name=first_name,
                last_name=last_name,
                defaults={
                    'id_number': enc.get('patient_id_number', ''),
                    'date_of_birth': date(1985, 1, 1),
                    'gender': 'O'
                }
            )

            dos_str = enc.get('date_of_service')
            try:
                dos = datetime.strptime(dos_str, '%Y-%m-%d').date() if dos_str else date.today()
            except ValueError:
                dos = date.today()

            claim = Claim.objects.create(
                practice=practice,
                patient=patient,
                date_of_service=dos,
                source_type='day_sheet',
                notes=f"Mobile Bedside Sync. Client UUID: {enc.get('client_encounter_id', 'N/A')}. Notes: {enc.get('notes', '')}".strip()
            )

            raw_amount = enc.get('amount_billed', '450.00')
            try:
                amount = Decimal(str(raw_amount))
            except Exception:
                amount = Decimal('450.00')

            ClaimLineItem.objects.create(
                claim=claim,
                tariff_code=enc.get('tariff_code', '0190'),
                tariff_description=enc.get('tariff_description', 'Consultation'),
                icd10_primary=enc.get('icd10', 'Z00.0'),
                quantity=1,
                amount_billed=amount
            )
            claim.recalculate_totals()

            created_claims.append({
                "client_encounter_id": enc.get("client_encounter_id"),
                "claim_id": claim.id,
                "status": claim.claim_status,
                "total_billed": f"{claim.total_billed:.2f}"
            })

    return JsonResponse({
        "status": "success",
        "device_id": body.get("device_id", "unknown"),
        "synced_count": len(created_claims),
        "claims": created_claims
    }, status=201)
