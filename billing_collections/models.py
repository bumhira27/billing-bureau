from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import TimeStampedModel

class PatientStatement(TimeStampedModel):
    SEND_VIA_CHOICES = [
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
        ('email', 'Email'),
        ('print', 'Print')
    ]
    DELIVERY_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('not_sent', 'Not Sent')
    ]

    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='statements')
    practice = models.ForeignKey('practices.Practice', on_delete=models.CASCADE, related_name='statements')
    statement_date = models.DateField(auto_now_add=True)
    total_outstanding = models.DecimalField(max_digits=12, decimal_places=2)
    sent_via = models.CharField(max_length=20, choices=SEND_VIA_CHOICES, blank=True)
    sent_date = models.DateTimeField(null=True, blank=True)
    delivery_status = models.CharField(max_length=20, choices=DELIVERY_STATUS_CHOICES, default='not_sent')
    message_content = models.TextField(blank=True)
    claims_included = models.ManyToManyField('claims.Claim', blank=True, related_name='statements')

    class Meta:
        ordering = ['-statement_date']
        verbose_name = 'Patient Statement'
        verbose_name_plural = 'Patient Statements'

    def __str__(self):
        return f'Statement for {self.patient} - {self.statement_date}'


class Payment(TimeStampedModel):
    PAYMENT_SOURCE_CHOICES = [
        ('medical_scheme', 'Medical Scheme'),
        ('patient_cash', 'Patient Cash'),
        ('patient_eft', 'Patient EFT'),
        ('patient_card', 'Patient Card')
    ]

    claim = models.ForeignKey('claims.Claim', on_delete=models.CASCADE, related_name='payments')
    claim_line_item = models.ForeignKey('claims.ClaimLineItem', on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    payment_source = models.CharField(max_length=20, choices=PAYMENT_SOURCE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    reference_number = models.CharField(max_length=100, blank=True)
    remittance_line = models.ForeignKey('reconciliation.RemittanceLine', on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-payment_date']
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'

    def __str__(self):
        return f'R{self.amount} on {self.payment_date} ({self.payment_source})'


@receiver(post_save, sender=Payment)
def update_claim_totals(sender, instance, created, **kwargs):
    if instance.claim and hasattr(instance.claim, 'recalculate_totals'):
        instance.claim.recalculate_totals()
