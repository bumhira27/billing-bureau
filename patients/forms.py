from django import forms
from .models import Patient, PatientScheme

class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        exclude = ['created_by']
        widgets = {
            'practice': forms.HiddenInput(),
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }

class PatientSchemeForm(forms.ModelForm):
    class Meta:
        model = PatientScheme
        exclude = ['created_by']
        widgets = {
            'patient': forms.HiddenInput(),
            'verified_date': forms.DateInput(attrs={'type': 'date'}),
        }

class PatientSearchForm(forms.Form):
    q = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Search patients...', 'class': 'form-control'}))
