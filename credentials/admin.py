from django.contrib import admin
from django import forms
from django.utils import timezone
from .models import MedicalAidPortalCredential


class MedicalAidPortalCredentialAdminForm(forms.ModelForm):
    class Meta:
        model = MedicalAidPortalCredential
        fields = '__all__'
        widgets = {
            'password': forms.PasswordInput(render_value=True),
        }


from django.utils.html import format_html


@admin.register(MedicalAidPortalCredential)
class MedicalAidPortalCredentialAdmin(admin.ModelAdmin):
    form = MedicalAidPortalCredentialAdminForm
    list_display = [
        'administrator',
        'username',
        'bureau_bhf_number',
        'is_active',
        'circuit_badge',
        'consecutive_failures',
        'last_status',
        'last_tested'
    ]
    list_filter = ['administrator', 'circuit_state', 'is_active']
    search_fields = ['username', 'bureau_bhf_number', 'portal_url']
    actions = ['test_selected_credentials', 'reset_selected_circuits']

    @admin.display(description="Circuit Breaker")
    def circuit_badge(self, obj):
        if obj.circuit_state == 'closed':
            return format_html('<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;">HEALTHY</span>')
        elif obj.circuit_state == 'open':
            return format_html('<span style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;">TRIPPED (PAUSED)</span>')
        else:
            return format_html('<span style="background-color: #ffc107; color: black; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;">HALF-OPEN</span>')

    @admin.action(description="Reset Circuit Breaker (force Healthy / Closed)")
    def reset_selected_circuits(self, request, queryset):
        for cred in queryset:
            cred.reset_circuit()
        self.message_user(request, f"Successfully reset circuit breaker on {queryset.count()} gateway credentials.")

    @admin.action(description="Verify authentication / test selected portal credentials")
    def test_selected_credentials(self, request, queryset):
        from claims.rpa.discovery_bot import DiscoveryPortalBot
        from claims.rpa.medscheme_bot import MedschemePortalBot
        from claims.rpa.simulator_bot import SimulatorPortalBot

        tested_count = 0
        for cred in queryset:
            if cred.administrator == 'discovery':
                bot = DiscoveryPortalBot(username=cred.username, password=cred.password, portal_url=cred.portal_url)
            elif cred.administrator == 'medscheme':
                bot = MedschemePortalBot(username=cred.username, password=cred.password, portal_url=cred.portal_url)
            else:
                bot = SimulatorPortalBot(username=cred.username, password=cred.password, portal_url=cred.portal_url)

            success = bot.verify_login()
            cred.last_tested = timezone.now()
            cred.last_status = "Authentication Verified" if success else "Authentication Failed"
            cred.save(update_fields=['last_tested', 'last_status'])
            tested_count += 1

        self.message_user(request, f"Successfully tested and updated {tested_count} portal credentials.")
