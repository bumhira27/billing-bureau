import logging
from datetime import date, timedelta
from decimal import Decimal
from celery import shared_task
from django.db.models import Sum
from django.db import transaction

from practices.models import Practice
from patients.models import Patient
from claims.models import Claim
from .models import PatientStatement, Payment

logger = logging.getLogger(__name__)

@shared_task
def generate_patient_statements_task():
    """
    Scheduled task that groups claims with outstanding patient liability
    and generates PatientStatement records.
    """
    # Find all claims where total_patient_liable > 0 and not fully paid
    outstanding_claims = Claim.objects.filter(total_patient_liable__gt=0).exclude(claim_status='paid')
    
    # Group by patient
    patients_with_debt = set(claim.patient for claim in outstanding_claims)
    
    generated_count = 0
    for patient in patients_with_debt:
        patient_claims = outstanding_claims.filter(patient=patient)
        
        # Calculate total outstanding
        total_outstanding = patient_claims.aggregate(total=Sum('total_patient_liable'))['total'] or Decimal('0.00')
        
        if total_outstanding > 0:
            with transaction.atomic():
                statement = PatientStatement.objects.create(
                    patient=patient,
                    practice=patient.practice,
                    total_outstanding=total_outstanding,
                    delivery_status='pending',
                    message_content=f"Dear {patient.first_name}, your medical aid short-paid your visit to {patient.practice.practice_name}. R{total_outstanding} is outstanding."
                )
                statement.claims_included.set(patient_claims)
                generated_count += 1
                
    logger.info(f"Generated {generated_count} Patient Statements.")
    return generated_count




