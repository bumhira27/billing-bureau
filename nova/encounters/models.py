from django.db import models
from core.models import TimeStampedModel, PublicIdModel, TenantModel

class Encounter(TimeStampedModel, PublicIdModel, TenantModel):
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='encounters')
    provider = models.ForeignKey('practices.Provider', on_delete=models.CASCADE, related_name='encounters')
    appointment = models.OneToOneField('scheduling.Appointment', on_delete=models.SET_NULL, null=True, blank=True)
    
    # SOAP Note
    subjective = models.TextField(blank=True, help_text="Reason for visit, history")
    objective = models.TextField(blank=True, help_text="Examination")
    assessment = models.TextField(blank=True, help_text="Diagnosis/Assessment")
    plan = models.TextField(blank=True, help_text="Treatment plan")
    
    is_signed = models.BooleanField(default=False)
    signed_at = models.DateTimeField(null=True, blank=True)
    signed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Encounter: {self.patient} on {self.created_at.date()}"

class VitalSign(TimeStampedModel, PublicIdModel, TenantModel):
    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name='vitals')
    height_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    systolic_bp = models.IntegerField(null=True, blank=True)
    diastolic_bp = models.IntegerField(null=True, blank=True)
    temperature_c = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    heart_rate = models.IntegerField(null=True, blank=True)

class Allergy(TimeStampedModel, PublicIdModel, TenantModel):
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='allergies')
    allergen = models.CharField(max_length=255)
    reaction = models.CharField(max_length=255, blank=True)
    severity = models.CharField(max_length=50, blank=True)

class Diagnosis(TimeStampedModel, PublicIdModel, TenantModel):
    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name='diagnoses')
    icd10_code = models.CharField(max_length=10)
    description = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)

class Procedure(TimeStampedModel, PublicIdModel, TenantModel):
    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name='procedures')
    tariff_code = models.CharField(max_length=20)
    description = models.CharField(max_length=255, blank=True)
    quantity = models.IntegerField(default=1)

class Prescription(TimeStampedModel, PublicIdModel, TenantModel):
    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name='prescriptions')
    medication_name = models.CharField(max_length=255)
    nappi_code = models.CharField(max_length=20, blank=True)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)
    instructions = models.TextField(blank=True)

class ClinicalDocument(TimeStampedModel, PublicIdModel, TenantModel):
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='documents')
    encounter = models.ForeignKey(Encounter, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='clinical_docs/')
    document_type = models.CharField(max_length=50, blank=True)
    uploaded_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
