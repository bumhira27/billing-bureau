from django.db import models
from core.models import TimeStampedModel

class Practice(TimeStampedModel):
    SWITCH_CHOICES = [
        ('mediswitch', 'MediSwitch'),
        ('healthbridge', 'Healthbridge'),
        ('medikredit', 'MediKredit'),
        ('none', 'None')
    ]

    practice_name = models.CharField(max_length=255)
    bhf_practice_number = models.CharField(max_length=20, unique=True, help_text='Board of Healthcare Funders practice number')
    hpcsa_number = models.CharField(max_length=20, help_text='HPCSA registration number')
    owner_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    physical_address = models.TextField(blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    switch_provider = models.CharField(max_length=20, choices=SWITCH_CHOICES, default='none')
    switch_account_id = models.CharField(max_length=50, blank=True)
    popia_agreement_signed_date = models.DateField(null=True, blank=True)
    service_agreement_signed_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    users = models.ManyToManyField('auth.User', related_name='assigned_practices', blank=True)

    class Meta:
        ordering = ['practice_name']
        verbose_name = 'Practice'
        verbose_name_plural = 'Practices'

    def __str__(self):
        return self.practice_name

    @property
    def is_compliant(self):
        return bool(self.popia_agreement_signed_date and self.service_agreement_signed_date)

