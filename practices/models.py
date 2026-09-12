from django.db import models
from core.models import TimeStampedModel

class Practice(TimeStampedModel):
    SWITCH_CHOICES = [
        ('mediswitch', 'MediSwitch'),
        ('healthbridge', 'Healthbridge'),
        ('medikredit', 'MediKredit'),
        ('none', 'None')
    ]
    FEE_TYPE_CHOICES = [
        ('percentage', 'Percentage of Collections'),
        ('fixed', 'Fixed Monthly Fee'),
        ('hybrid', 'Hybrid (Fixed + Percentage)')
    ]

    practice_name = models.CharField(max_length=255)
    bhf_practice_number = models.CharField(max_length=20, unique=True, help_text='Board of Healthcare Funders practice number')
    hpcsa_number = models.CharField(max_length=20, help_text='HPCSA registration number')
    owner_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    physical_address = models.TextField(blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account_number = models.CharField(max_length=30, blank=True)
    bank_branch_code = models.CharField(max_length=10, blank=True)
    switch_provider = models.CharField(max_length=20, choices=SWITCH_CHOICES, default='none')
    switch_account_id = models.CharField(max_length=50, blank=True)
    fee_type = models.CharField(max_length=20, choices=FEE_TYPE_CHOICES, default='percentage')
    fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=2.00, help_text='Percentage fee on collected revenue')
    fee_fixed_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Fixed monthly fee in Rands')
    popia_agreement_signed_date = models.DateField(null=True, blank=True)
    service_agreement_signed_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['practice_name']
        verbose_name = 'Practice'
        verbose_name_plural = 'Practices'

    def __str__(self):
        return self.practice_name

    @property
    def is_compliant(self):
        return bool(self.popia_agreement_signed_date and self.service_agreement_signed_date)


class PortalCredential(TimeStampedModel):
    ADMINISTRATOR_CHOICES = [
        ('discovery', 'Discovery Health Provider Portal'),
        ('medscheme', 'Medscheme / GEMS Provider Portal'),
        ('momentum', 'Momentum / Metropolitan Online'),
        ('universal', 'Universal Healthcare Portal'),
        ('simulator', 'Direct Portal Simulator (Dry-Run Test)'),
    ]

    practice = models.ForeignKey(Practice, on_delete=models.CASCADE, related_name='portal_credentials')
    administrator = models.CharField(max_length=50, choices=ADMINISTRATOR_CHOICES)
    portal_url = models.URLField(blank=True)
    username = models.CharField(max_length=100, help_text="Practice portal username or practice number")
    password = models.CharField(max_length=255, help_text="Stored password for headless browser login")
    is_active = models.BooleanField(default=True)
    last_tested = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['practice', 'administrator']
        verbose_name = 'Portal Credential'
        verbose_name_plural = 'Portal Credentials'
        unique_together = [['practice', 'administrator']]

    def __str__(self):
        return f"{self.practice.practice_name} - {self.get_administrator_display()}"

