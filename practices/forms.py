from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, Div, Row, Column
from .models import Practice, PortalCredential

class PracticeForm(forms.ModelForm):
    class Meta:
        model = Practice
        exclude = [
            'created_by',
            'bank_name',
            'bank_account_number',
            'bank_branch_code',
            'fee_type',
            'fee_percentage',
            'fee_fixed_amount',
        ]
        widgets = {
            'popia_agreement_signed_date': forms.DateInput(attrs={'type': 'date'}),
            'service_agreement_signed_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset(
                'Practice Details',
                Row(
                    Column('practice_name', css_class='form-group col-md-6 mb-0'),
                    Column('owner_name', css_class='form-group col-md-6 mb-0'),
                    css_class='form-row'
                ),
                Row(
                    Column('bhf_practice_number', css_class='form-group col-md-6 mb-0'),
                    Column('hpcsa_number', css_class='form-group col-md-6 mb-0'),
                    css_class='form-row'
                )
            ),
            Fieldset(
                'Contact',
                Row(
                    Column('phone', css_class='form-group col-md-6 mb-0'),
                    Column('email', css_class='form-group col-md-6 mb-0'),
                    css_class='form-row'
                ),
                'physical_address',
                'postal_code'
            ),
            Fieldset(
                'Switch Integration',
                Row(
                    Column('switch_provider', css_class='form-group col-md-6 mb-0'),
                    Column('switch_account_id', css_class='form-group col-md-6 mb-0'),
                    css_class='form-row'
                )
            ),
            Fieldset(
                'Compliance',
                Row(
                    Column('popia_agreement_signed_date', css_class='form-group col-md-6 mb-0'),
                    Column('service_agreement_signed_date', css_class='form-group col-md-6 mb-0'),
                    css_class='form-row'
                ),
                'is_active'
            )
        )


class PortalCredentialForm(forms.ModelForm):
    class Meta:
        model = PortalCredential
        fields = ['administrator', 'portal_url', 'username', 'password', 'is_active']
        widgets = {
            'password': forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}),
            'administrator': forms.Select(attrs={'class': 'form-select'}),
            'portal_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Optional gateway URL'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
