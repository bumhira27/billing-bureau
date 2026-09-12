from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, ListView, DetailView, FormView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from .models import RemittanceFile, RemittanceLine, ReconciliationLog
from .forms import RemittanceFileUploadForm, ManualMatchForm
from .tasks import process_remittance_file
from claims.models import ClaimLineItem

class ReconciliationDashboardView(TemplateView):
    template_name = 'reconciliation/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        files = RemittanceFile.objects.all()
        lines = RemittanceLine.objects.all()
        context['recent_files'] = files[:10]
        context['total_files'] = files.count()
        matched_lines = lines.filter(match_status__in=['auto_matched', 'manual_matched']).count()
        total_lines = lines.count()
        context['total_matched'] = matched_lines
        context['total_unmatched'] = lines.filter(match_status='unmatched').count()
        context['match_rate'] = (matched_lines / total_lines * 100) if total_lines > 0 else 0
        return context

class RemittanceFileListView(ListView):
    model = RemittanceFile
    template_name = 'reconciliation/remittancefile_list.html'
    context_object_name = 'files'
    paginate_by = 20

class RemittanceFileDetailView(DetailView):
    model = RemittanceFile
    template_name = 'reconciliation/remittancefile_detail.html'
    context_object_name = 'file'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lines'] = self.object.lines.all()
        return context

class RemittanceFileUploadView(FormView):
    template_name = 'reconciliation/remittancefile_upload.html'
    form_class = RemittanceFileUploadForm

    def form_valid(self, form):
        file = form.cleaned_data['file']
        switch_provider = form.cleaned_data['switch_provider']
        payment_date = form.cleaned_data['payment_date']
        
        # Prevent duplicate uploads
        existing = RemittanceFile.objects.filter(file_name=file.name).first()
        if existing:
            messages.warning(self.request, f"Remittance file '{file.name}' was already uploaded and processed on {existing.received_date}. Viewing existing record.")
            return redirect('reconciliation:file_detail', pk=existing.pk)

        remittance_file = RemittanceFile.objects.create(
            file_name=file.name,
            file=file,
            switch_provider=switch_provider,
            payment_date=payment_date
        )
        
        process_remittance_file.delay(remittance_file.id)
        messages.success(self.request, f"File {file.name} uploaded and is being processed.")
        return redirect('reconciliation:file_detail', pk=remittance_file.pk)

class UnmatchedLinesView(ListView):
    model = RemittanceLine
    template_name = 'reconciliation/unmatched_list.html'
    context_object_name = 'lines'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().filter(match_status='unmatched')
        q = self.request.GET.get('q')
        practice = self.request.GET.get('practice')
        if q:
            qs = qs.filter(membership_number__icontains=q)
        if practice:
            qs = qs.filter(practice_number__icontains=practice)
        return qs

from decimal import Decimal
from django.db import transaction

def manual_match_view(request):
    if request.method == 'POST':
        form = ManualMatchForm(request.POST)
        if form.is_valid():
            remittance_line_id = form.cleaned_data['remittance_line_id']
            claim_line_item_id = form.cleaned_data['claim_line_item_id']
            notes = form.cleaned_data['notes']

            with transaction.atomic():
                remittance_line = get_object_or_404(RemittanceLine.objects.select_for_update(), id=remittance_line_id)
                claim_line_item = get_object_or_404(ClaimLineItem.objects.select_for_update(), id=claim_line_item_id)

                remittance_line.matched_claim_line_item = claim_line_item
                remittance_line.match_status = 'manual_matched'
                remittance_line.save(update_fields=['matched_claim_line_item', 'match_status'])

                claim_line_item.amount_paid = remittance_line.amount_paid
                claim_line_item.amount_patient_liable = max(Decimal('0.00'), claim_line_item.amount_billed - claim_line_item.amount_paid - claim_line_item.amount_scheme_discount)
                if claim_line_item.amount_paid == 0:
                    claim_line_item.line_status = 'rejected'
                elif claim_line_item.amount_paid >= claim_line_item.amount_billed:
                    claim_line_item.line_status = 'paid'
                else:
                    claim_line_item.line_status = 'short_paid'
                claim_line_item.save()

                claim_line_item.claim.recalculate_totals()

                matched_user = request.user if request.user.is_authenticated else None
                ReconciliationLog.objects.create(
                    remittance_line=remittance_line,
                    claim_line_item=claim_line_item,
                    match_method='manual',
                    matched_by=matched_user,
                    notes=notes
                )

            messages.success(request, 'Manually matched successfully.')
            return redirect(request.META.get('HTTP_REFERER', reverse('reconciliation:dashboard')))
    return redirect('reconciliation:dashboard')
