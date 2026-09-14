from django.contrib import admin
from .models import Practice

@admin.register(Practice)
class PracticeAdmin(admin.ModelAdmin):
    list_display = ['practice_name', 'bhf_practice_number', 'owner_name', 'phone', 'is_active', 'switch_provider']
    list_filter = ['is_active', 'switch_provider']
    search_fields = ['practice_name', 'bhf_practice_number', 'owner_name']
