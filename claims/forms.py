from django import forms
from django.forms import inlineformset_factory
from .models import Claim, ClaimLineItem

class ClaimForm(forms.ModelForm):
    class Meta:
        model = Claim
        fields = [
            'practice', 'patient', 'patient_scheme', 'date_of_service',
            'referring_doctor_bhf', 'referring_doctor_name', 'authorization_number',
            'notes'
        ]
        widgets = {
            'patient': forms.HiddenInput(),
            'date_of_service': forms.DateInput(attrs={'type': 'date'}),
        }

class ClaimLineItemForm(forms.ModelForm):
    class Meta:
        model = ClaimLineItem
        fields = [
            'tariff_code', 'tariff_description', 'icd10_primary',
            'icd10_secondary', 'icd10_tertiary', 'quantity',
            'amount_billed', 'modifier_codes', 'nappi_code'
        ]
        widgets = {
            'tariff_code': forms.TextInput(attrs={'autocomplete': 'off', 'class': 'tariff-autocomplete'}),
            'icd10_primary': forms.TextInput(attrs={'autocomplete': 'off', 'class': 'icd10-autocomplete'}),
            'icd10_secondary': forms.TextInput(attrs={'autocomplete': 'off', 'class': 'icd10-autocomplete'}),
            'icd10_tertiary': forms.TextInput(attrs={'autocomplete': 'off', 'class': 'icd10-autocomplete'}),
        }

ClaimLineItemFormSet = inlineformset_factory(
    Claim, 
    ClaimLineItem, 
    form=ClaimLineItemForm, 
    extra=3, 
    can_delete=True
)

