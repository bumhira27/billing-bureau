from django.contrib import admin
from .models import Patient, PatientScheme

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'id_number', 'practice', 'phone']
    list_filter = ['practice', 'gender']
    search_fields = ['first_name', 'last_name', 'id_number']

@admin.register(PatientScheme)
class PatientSchemeAdmin(admin.ModelAdmin):
    list_display = ['patient', 'scheme_name', 'membership_number', 'dependent_code', 'is_active']
    list_filter = ['scheme_name', 'is_active']
    search_fields = ['patient__first_name', 'patient__last_name', 'scheme_name', 'membership_number']
