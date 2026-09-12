from django.urls import reverse_lazy
from django.views.generic import ListView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from .models import BureauProfile, PracticeInvoice

class BureauProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = BureauProfile
    fields = ['name', 'logo', 'default_commission_rate', 'tax_number', 'contact_details']
    template_name = 'bureau/bureauprofile_form.html'
    success_url = reverse_lazy('bureau:profile_update')

    def get_object(self, queryset=None):
        obj, created = BureauProfile.objects.get_or_create(
            defaults={'name': 'Billing Bureau', 'default_commission_rate': 0.00}
        )
        return obj

    def form_valid(self, form):
        messages.success(self.request, "Bureau profile updated successfully.")
        return super().form_valid(form)


class PracticeInvoiceListView(LoginRequiredMixin, ListView):
    model = PracticeInvoice
    template_name = 'bureau/practiceinvoice_list.html'
    context_object_name = 'invoices'

    def get_queryset(self):
        return PracticeInvoice.objects.select_related('practice').all()
