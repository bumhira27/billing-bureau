from decimal import Decimal
from django.db import models
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import TimeStampedModel

class Claim(TimeStampedModel):
    CLAIM_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('requires_correction', 'Requires Correction'),
        ('submitted', 'Submitted'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid in Full'),
        ('partially_paid', 'Partially Paid'),
        ('appealed', 'Under Appeal'),
        ('written_off', 'Written Off')
    ]

    SOURCE_TYPE_CHOICES = [
        ('manual', 'Manual Capture'),
        ('photo', 'Photo/Scan Upload'),
        ('day_sheet', 'Day Sheet')
    ]

    practice = models.ForeignKey('practices.Practice', on_delete=models.CASCADE, related_name='claims')
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='claims')
    patient_scheme = models.ForeignKey('patients.PatientScheme', on_delete=models.SET_NULL, null=True, blank=True, related_name='claims')
    date_of_service = models.DateField()
    referring_doctor_bhf = models.CharField(max_length=20, blank=True)
    referring_doctor_name = models.CharField(max_length=255, blank=True)
    authorization_number = models.CharField(max_length=50, blank=True)
    claim_status = models.CharField(max_length=20, choices=CLAIM_STATUS_CHOICES, default='draft')
    submission_date = models.DateField(null=True, blank=True)
    switch_reference_number = models.CharField(max_length=100, blank=True)
    
    total_billed = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_patient_liable = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPE_CHOICES, default='manual')
    source_file = models.ImageField(upload_to='claim_sources/%Y/%m/', blank=True, null=True)
    notes = models.TextField(blank=True)
    
    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low')
    ]
    assigned_to = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_claims')
    internal_priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')

    class Meta:
        ordering = ['-date_of_service', '-created_at']
        verbose_name = 'Claim'
        verbose_name_plural = 'Claims'

    def __str__(self):
        return f'Claim {self.id} - {self.patient} ({self.date_of_service})'

    @property
    def outstanding_balance(self):
        return self.total_billed - self.total_paid

    @property
    def is_fully_paid(self):
        return self.total_paid >= self.total_billed and self.total_billed > 0

    def recalculate_totals(self):
        """
        Sums line items and updates total_billed, total_paid, total_patient_liable.
        """
        totals = self.line_items.aggregate(
            total_billed=Sum('amount_billed'),
            total_paid=Sum('amount_paid'),
            total_patient_liable=Sum('amount_patient_liable')
        )
        self.total_billed = round(Decimal(str(totals['total_billed'] or 0)), 2)
        self.total_paid = round(Decimal(str(totals['total_paid'] or 0)), 2)
        self.total_patient_liable = round(Decimal(str(totals['total_patient_liable'] or 0)), 2)

        if self.total_billed > 0:
            if self.total_paid >= self.total_billed:
                self.claim_status = 'paid'
            elif self.total_paid > 0:
                self.claim_status = 'partially_paid'
            elif self.line_items.filter(line_status='rejected').count() == self.line_items.count() and self.line_items.exists():
                self.claim_status = 'rejected'

        self.save()

class ClaimLineItem(models.Model):
    LINE_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid in Full'),
        ('short_paid', 'Short Paid'),
        ('rejected', 'Rejected'),
        ('appealed', 'Under Appeal')
    ]

    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='line_items')
    tariff_code = models.CharField(max_length=20)
    tariff_description = models.CharField(max_length=500, blank=True)
    icd10_primary = models.CharField(max_length=10)
    icd10_secondary = models.CharField(max_length=10, blank=True)
    icd10_tertiary = models.CharField(max_length=10, blank=True)
    quantity = models.IntegerField(default=1)
    amount_billed = models.DecimalField(max_digits=10, decimal_places=2)
    modifier_codes = models.JSONField(default=list, blank=True)
    nappi_code = models.CharField(max_length=20, blank=True)
    
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_patient_liable = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_scheme_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    line_status = models.CharField(max_length=20, choices=LINE_STATUS_CHOICES, default='pending')
    rejection_code = models.CharField(max_length=20, blank=True)
    rejection_description = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ['id']
        verbose_name = 'Claim Line Item'
        verbose_name_plural = 'Claim Line Items'

    def __str__(self):
        return f'{self.tariff_code} - R{self.amount_billed}'

@receiver(post_save, sender=ClaimLineItem)
def update_claim_totals(sender, instance, **kwargs):
    instance.claim.recalculate_totals()


class ClaimNote(TimeStampedModel):
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='claim_notes')
    author = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='claim_notes')
    text = models.TextField()

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Claim Note'
        verbose_name_plural = 'Claim Notes'

    def __str__(self):
        return f'Note on {self.claim} by {self.author.username}'


class RpaSubmissionLog(TimeStampedModel):
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='rpa_submissions')
    portal_name = models.CharField(max_length=100)
    success = models.BooleanField(default=False)
    reference_number = models.CharField(max_length=100, blank=True)
    message = models.TextField(blank=True)
    screenshot = models.ImageField(upload_to='rpa_proofs/%Y/%m/', null=True, blank=True)
    execution_time_seconds = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'RPA Submission Log'
        verbose_name_plural = 'RPA Submission Logs'

    def __str__(self):
        return f"RPA {self.portal_name} on Claim {self.claim_id} - {'Success' if self.success else 'Failed'}"

