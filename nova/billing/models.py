from django.db import models
from core.models import TimeStampedModel, PublicIdModel, TenantModel
from decimal import Decimal

class Invoice(TimeStampedModel, PublicIdModel, TenantModel):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('finalized', 'Finalized'),
        ('paid', 'Paid'),
        ('void', 'Void'),
    ]

    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='invoices')
    encounter = models.OneToOneField('encounters.Encounter', on_delete=models.SET_NULL, null=True, blank=True)
    
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    @property
    def balance_due(self):
        return self.total_amount - self.amount_paid

class Charge(TimeStampedModel, PublicIdModel, TenantModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='charges')
    procedure = models.ForeignKey('encounters.Procedure', on_delete=models.SET_NULL, null=True, blank=True)
    tariff_code = models.CharField(max_length=20)
    description = models.CharField(max_length=255)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)

class Payment(TimeStampedModel, PublicIdModel, TenantModel):
    METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
        ('eft', 'EFT'),
        ('medical_aid', 'Medical Aid'),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    reference = models.CharField(max_length=100, blank=True)
    receipt_number = models.CharField(max_length=100, blank=True)

class ClaimDraft(TimeStampedModel, PublicIdModel, TenantModel):
    """
    Represents the Nova side of a claim before/during its transmission to Billing Bureau.
    """
    STATE_CHOICES = [
        ('not_sent', 'Not Sent'),
        ('pending', 'Pending Transmission'),
        ('sent', 'Sent to Bureau'),
        ('accepted', 'Accepted by Bureau'),
        ('rejected', 'Rejected by Bureau'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid in Full'),
        ('needs_correction', 'Needs Correction'),
        ('failed_retryable', 'Failed (Retryable)'),
    ]

    invoice = models.OneToOneField(Invoice, on_delete=models.CASCADE, related_name='claim_draft')
    bureau_public_id = models.UUIDField(null=True, blank=True, help_text="ID of the claim in Billing Bureau")
    state = models.CharField(max_length=20, choices=STATE_CHOICES, default='not_sent')
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
