from django import forms
from django.forms import inlineformset_factory
from .models import Claim, ClaimLineItem

class ClaimForm(forms.ModelForm):
    class Meta:
        model = Claim
        fields = [
            'practice', 'patient', 'patient_scheme', 'date_of_service',
            'referring_doctor_bhf', 'referring_doctor_name', 'authorization_number',
            'source_type', 'source_file', 'notes'
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

class NoteUploadForm(forms.Form):
    practice = forms.ModelChoiceField(
        queryset=None,
        empty_label="-- Select Practice --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    note_file = forms.FileField(
        label="Handwritten Note / Day Sheet Image",
        widget=forms.FileInput(attrs={'accept': 'image/*', 'class': 'form-control', 'id': 'note_file_input'})
    )
    notes = forms.CharField(
        required=False,
        label="Optional Instructions",
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'Doctor name, specialty context, or specific instructions'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from practices.models import Practice
        self.fields['practice'].queryset = Practice.objects.filter(is_active=True)

