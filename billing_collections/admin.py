from django.contrib import admin
from .models import PatientStatement, Payment

@admin.register(PatientStatement)
class PatientStatementAdmin(admin.ModelAdmin):
    list_display = ('patient', 'practice', 'statement_date', 'total_outstanding', 'sent_via', 'delivery_status')
    list_filter = ('delivery_status', 'sent_via', 'practice')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('claim', 'payment_source', 'amount', 'payment_date', 'reference_number')
    list_filter = ('payment_source',)
    search_fields = ('reference_number', 'claim__patient__last_name')
