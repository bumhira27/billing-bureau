from django.contrib import admin
from .models import BureauProfile, PracticeInvoice, PracticeInvoiceLineItem

@admin.register(BureauProfile)
class BureauProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'default_commission_rate', 'tax_number', 'updated_at']
    search_fields = ['name', 'tax_number']

class PracticeInvoiceLineItemInline(admin.TabularInline):
    model = PracticeInvoiceLineItem
    extra = 1

@admin.register(PracticeInvoice)
class PracticeInvoiceAdmin(admin.ModelAdmin):
    list_display = ['practice', 'invoice_month', 'total_collected', 'commission_amount', 'status', 'created_at']
    list_filter = ['status', 'invoice_month', 'practice']
    search_fields = ['practice__name']
    inlines = [PracticeInvoiceLineItemInline]
    date_hierarchy = 'invoice_month'
