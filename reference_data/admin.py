from django.contrib import admin
from .models import ICD10Code, TariffCode, RejectionCode

@admin.register(ICD10Code)
class ICD10CodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'description', 'category', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('code', 'description')

@admin.register(TariffCode)
class TariffCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'description', 'category', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('code', 'description')

@admin.register(RejectionCode)
class RejectionCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'description', 'category', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('code', 'description')
