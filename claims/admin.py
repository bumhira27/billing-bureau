from django.contrib import admin
from .models import Claim, ClaimLineItem

class ClaimLineItemInline(admin.TabularInline):
    model = ClaimLineItem
    extra = 1

@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'practice', 'date_of_service', 'claim_status', 'total_billed', 'total_paid')
    list_filter = ('claim_status', 'practice', 'source_type')
    search_fields = ('patient__first_name', 'patient__last_name', 'switch_reference_number')
    date_hierarchy = 'date_of_service'
    inlines = [ClaimLineItemInline]

@admin.register(ClaimLineItem)
class ClaimLineItemAdmin(admin.ModelAdmin):
    list_display = ('claim', 'tariff_code', 'icd10_primary', 'amount_billed', 'amount_paid', 'line_status')
    list_filter = ('line_status',)
