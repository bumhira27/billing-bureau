from django.db import models
from django.db.models import JSONField
from core.models import TimeStampedModel

class RemittanceFile(TimeStampedModel):
    SWITCH_CHOICES = [
        ('mediswitch', 'MediSwitch'),
        ('healthbridge', 'Healthbridge'),
        ('medikredit', 'MediKredit'),
        ('manual', 'Manual Upload'),
        ('other', 'Other')
    ]
    switch_provider = models.CharField(max_length=20, choices=SWITCH_CHOICES, default='manual')
    file_name = models.CharField(max_length=255)
    file = models.FileField(upload_to='remittance_files/%Y/%m/')
    received_date = models.DateField(auto_now_add=True)
    payment_date = models.DateField(null=True, blank=True)
    total_records = models.IntegerField(default=0)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    
    PROCESS_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('error', 'Error')
    ]
    processed_status = models.CharField(max_length=20, choices=PROCESS_STATUS_CHOICES, default='pending')
    raw_content = JSONField(default=dict, blank=True)
    error_log = models.TextField(blank=True)
    records_matched = models.IntegerField(default=0)
    records_unmatched = models.IntegerField(default=0)

    class Meta:
        ordering = ['-received_date']
        verbose_name = 'Remittance File'
        verbose_name_plural = 'Remittance Files'

    def __str__(self):
        return f"{self.file_name} ({self.received_date})"

class RemittanceLine(models.Model):
    remittance_file = models.ForeignKey(RemittanceFile, on_delete=models.CASCADE, related_name='lines')
    practice_number = models.CharField(max_length=20)
    scheme_name = models.CharField(max_length=255, blank=True)
    membership_number = models.CharField(max_length=50)
    dependent_code = models.CharField(max_length=5, blank=True)
    patient_name = models.CharField(max_length=255, blank=True)
    date_of_service = models.DateField()
    tariff_code = models.CharField(max_length=20)
    amount_claimed = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_approved = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reason_code = models.CharField(max_length=20, blank=True)
    reason_description = models.CharField(max_length=500, blank=True)
    
    MATCH_STATUS_CHOICES = [
        ('unmatched', 'Unmatched'),
        ('auto_matched', 'Auto Matched'),
        ('manual_matched', 'Manually Matched'),
        ('no_match', 'No Match Found')
    ]
    match_status = models.CharField(max_length=20, choices=MATCH_STATUS_CHOICES, default='unmatched')
    matched_claim_line_item = models.ForeignKey('claims.ClaimLineItem', on_delete=models.SET_NULL, null=True, blank=True, related_name='remittance_matches')

    class Meta:
        ordering = ['id']
        verbose_name = 'Remittance Line'
        verbose_name_plural = 'Remittance Lines'

    def __str__(self):
        return f"{self.practice_number} - {self.membership_number} - {self.tariff_code} ({self.date_of_service})"

class ReconciliationLog(TimeStampedModel):
    remittance_line = models.ForeignKey(RemittanceLine, on_delete=models.CASCADE, related_name='match_logs')
    claim_line_item = models.ForeignKey('claims.ClaimLineItem', on_delete=models.SET_NULL, null=True, blank=True)
    
    MATCH_METHOD_CHOICES = [
        ('auto_exact', 'Automatic Exact Match'),
        ('auto_fuzzy', 'Automatic Fuzzy Match'),
        ('manual', 'Manual Match')
    ]
    match_method = models.CharField(max_length=20, choices=MATCH_METHOD_CHOICES)
    match_confidence = models.IntegerField(default=0, help_text='0-100')
    matched_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Reconciliation Log'
        verbose_name_plural = 'Reconciliation Logs'

    def __str__(self):
        return f"Log for {self.remittance_line}"
