from django import forms
from django.utils import timezone
from .models import Payment, PatientStatement
from practices.models import Practice

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['claim', 'claim_line_item', 'payment_source', 'amount', 'payment_date', 'reference_number', 'notes']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'claim' in self.data:
            try:
                claim_id = int(self.data.get('claim'))
                self.fields['claim_line_item'].queryset = self.fields['claim_line_item'].queryset.filter(claim_id=claim_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.claim:
            self.fields['claim_line_item'].queryset = self.instance.claim.line_items.all()
        else:
            self.fields['claim_line_item'].queryset = self.fields['claim_line_item'].queryset.none()


class GenerateStatementForm(forms.Form):
    practice = forms.ModelChoiceField(queryset=Practice.objects.filter(is_active=True))
    as_of_date = forms.DateField(initial=timezone.now().date, widget=forms.DateInput(attrs={'type': 'date'}))
    min_outstanding = forms.DecimalField(initial=0, help_text='Minimum outstanding balance to include', max_digits=10, decimal_places=2)
    send_via = forms.ChoiceField(choices=PatientStatement.SEND_VIA_CHOICES + [('', 'Do not send')], required=False)
