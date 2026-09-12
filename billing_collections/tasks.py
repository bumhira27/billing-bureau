import logging
from datetime import date, timedelta
from decimal import Decimal
from celery import shared_task
from django.db.models import Sum
from django.db import transaction

from practices.models import Practice
from patients.models import Patient
from claims.models import Claim
from .models import PatientStatement, Payment, BureauInvoice, BureauInvoiceLine

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


@shared_task
def generate_bureau_invoices_task():
    """
    Scheduled task (run on 1st of month) to generate Bureau Invoices for 
    commission fees on the previous month's collections.
    """
    today = date.today()
    # Find the start and end of the previous month
    first_day_of_this_month = today.replace(day=1)
    last_day_of_prev_month = first_day_of_this_month - timedelta(days=1)
    first_day_of_prev_month = last_day_of_prev_month.replace(day=1)
    
    practices = Practice.objects.all()
    
    generated_count = 0
    for practice in practices:
        # Get all payments made in the previous month for this practice
        payments = Payment.objects.filter(
            claim__practice=practice,
            payment_date__gte=first_day_of_prev_month,
            payment_date__lte=last_day_of_prev_month
        )
        
        if not payments.exists():
            continue
            
        total_collected = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        if total_collected > 0:
            commission_rate = practice.fee_percentage or Decimal('2.00')
            
            with transaction.atomic():
                # Avoid duplicate invoices
                invoice, created = BureauInvoice.objects.get_or_create(
                    practice=practice,
                    billing_period_start=first_day_of_prev_month,
                    billing_period_end=last_day_of_prev_month,
                    defaults={
                        'total_collections_processed': total_collected,
                        'commission_rate': commission_rate,
                        'invoice_total': Decimal('0.00'), # Will calculate below
                        'status': 'draft'
                    }
                )
                
                if created:
                    invoice_total = Decimal('0.00')
                    for payment in payments:
                        commission_fee = (payment.amount * commission_rate) / Decimal('100.00')
                        BureauInvoiceLine.objects.create(
                            invoice=invoice,
                            payment=payment,
                            description=f"Collection commission for claim #{payment.claim.id} ({payment.payment_source})",
                            payment_amount=payment.amount,
                            commission_fee=commission_fee
                        )
                        invoice_total += commission_fee
                        
                    invoice.invoice_total = invoice_total
                    invoice.save(update_fields=['invoice_total'])
                    generated_count += 1
                    
    logger.info(f"Generated {generated_count} Bureau Invoices.")
    return generated_count
