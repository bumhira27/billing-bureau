from django import forms
from .models import RemittanceFile

class RemittanceFileUploadForm(forms.Form):
    file = forms.FileField()
    switch_provider = forms.ChoiceField(choices=RemittanceFile.SWITCH_CHOICES)
    payment_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

class ManualMatchForm(forms.Form):
    remittance_line_id = forms.IntegerField(widget=forms.HiddenInput)
    claim_line_item_id = forms.IntegerField()
    notes = forms.CharField(required=False, widget=forms.Textarea)
