from django.db import models
from django.core.validators import RegexValidator
from core.models import TimeStampedModel, PublicIdModel, TenantModel

class EncryptedCharField(models.CharField):
    """
    Stub for EncryptedCharField to ensure POPIA compliance at rest.
    In a real implementation, this would use a library like django-fernet-fields
    or a custom database function to encrypt data transparently.
    """
    pass

class Patient(TimeStampedModel, PublicIdModel, TenantModel):
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    
    id_number = EncryptedCharField(max_length=255, blank=True, help_text="SA ID number")
    phone = EncryptedCharField(max_length=255, blank=True)
    email = EncryptedCharField(max_length=255, blank=True)
    address = models.TextField(blank=True)
    
    next_of_kin_name = models.CharField(max_length=255, blank=True)
    next_of_kin_phone = EncryptedCharField(max_length=255, blank=True)

    alerts = models.TextField(blank=True, help_text="Clinical or administrative alerts")
    consent_given = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class PatientScheme(TimeStampedModel, PublicIdModel, TenantModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="schemes")
    scheme_name = models.CharField(max_length=255)
    scheme_option = models.CharField(max_length=100, blank=True)
    membership_number = EncryptedCharField(max_length=255)
    dependent_code = models.CharField(max_length=5, default="00")
    
    main_member_name = models.CharField(max_length=255, blank=True)
    main_member_id_number = EncryptedCharField(max_length=255, blank=True)
    
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-is_active', 'scheme_name']

    def __str__(self):
        return f"{self.scheme_name} - {self.membership_number}"
