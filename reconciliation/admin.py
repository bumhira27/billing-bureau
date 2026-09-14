from django.contrib import admin
from .models import RemittanceFile, RemittanceLine, ReconciliationLog, ClearinghouseConfig

@admin.register(RemittanceFile)
class RemittanceFileAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'switch_provider', 'received_date', 'processed_status', 'total_records', 'records_matched', 'records_unmatched')
    list_filter = ('processed_status', 'switch_provider')
    search_fields = ('file_name',)

@admin.register(RemittanceLine)
class RemittanceLineAdmin(admin.ModelAdmin):
    list_display = ('practice_number', 'membership_number', 'date_of_service', 'tariff_code', 'amount_paid', 'match_status')
    list_filter = ('match_status',)
    search_fields = ('membership_number', 'practice_number', 'tariff_code')

admin.site.register(ReconciliationLog)

@admin.register(ClearinghouseConfig)
class ClearinghouseConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'sftp_host', 'sftp_username', 'is_active')

