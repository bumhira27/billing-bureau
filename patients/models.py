from django.db import models
from django.core.validators import RegexValidator
from core.models import TimeStampedModel
from core.fields import EncryptedCharField
from practices.models import Practice

class Patient(TimeStampedModel):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    practice = models.ForeignKey(Practice, on_delete=models.CASCADE, related_name='patients')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    id_number = EncryptedCharField(
        max_length=255, 
        blank=True, 
        help_text='SA ID number',
        validators=[RegexValidator(r'^\d{13}$', 'Enter a valid 13-digit SA ID number.')]
    )
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    phone = EncryptedCharField(max_length=255, blank=True)
    email = EncryptedCharField(max_length=255, blank=True)
    physical_address = models.TextField(blank=True)
    postal_code = models.CharField(max_length=10, blank=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        unique_together = [['practice', 'id_number']]
        verbose_name = 'Patient'
        verbose_name_plural = 'Patients'

    def __str__(self):
        return f"{self.last_name}, {self.first_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def active_scheme(self):
        return self.schemes.filter(is_active=True).first()

class PatientScheme(TimeStampedModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='schemes')
    scheme_name = models.CharField(max_length=255)
    scheme_option = models.CharField(max_length=100, blank=True)
    membership_number = EncryptedCharField(max_length=255)
    dependent_code = models.CharField(max_length=5, default='00')
    main_member_name = models.CharField(max_length=255, blank=True)
    main_member_id_number = EncryptedCharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    verified_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-is_active', 'scheme_name']
        verbose_name = 'Patient Scheme'
        verbose_name_plural = 'Patient Schemes'

    def __str__(self):
        return f"{self.scheme_name} - {self.membership_number} (dep {self.dependent_code})"

class PHIReadAudit(TimeStampedModel):
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    endpoint = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'PHI Read Audit'
        verbose_name_plural = 'PHI Read Audits'

    def __str__(self):
        return f"{self.user} read {self.patient} at {self.created_at}"
