from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .models import Claim, ClaimLineItem
from .forms import ClaimForm, ClaimLineItemFormSet
from .services.ai_extractor import extract_from_image
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)
from core.mixins import RBACQuerySetMixin
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

class ClaimListView(LoginRequiredMixin, RBACQuerySetMixin, ListView):
    model = Claim
    template_name = 'claims/claim_list.html'
    context_object_name = 'claims'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset()
        
        practice_id = self.request.GET.get('practice')
        status = self.request.GET.get('status')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        q = self.request.GET.get('q')

        if practice_id:
            queryset = queryset.filter(practice_id=practice_id)
        if status:
            queryset = queryset.filter(claim_status=status)
        if date_from:
            queryset = queryset.filter(date_of_service__gte=date_from)
        if date_to:
            queryset = queryset.filter(date_of_service__lte=date_to)
        if q:
            queryset = queryset.filter(
                Q(patient__first_name__icontains=q) |
                Q(patient__last_name__icontains=q) |
                Q(switch_reference_number__icontains=q)
            )
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_practice'] = self.request.GET.get('practice', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['current_date_from'] = self.request.GET.get('date_from', '')
        context['current_date_to'] = self.request.GET.get('date_to', '')
        context['current_q'] = self.request.GET.get('q', '')
        
        from practices.models import Practice
        context['practices'] = Practice.objects.all()
        context['statuses'] = Claim.CLAIM_STATUS_CHOICES
        return context

class ClaimDetailView(LoginRequiredMixin, RBACQuerySetMixin, DetailView):
    model = Claim
    template_name = 'claims/claim_detail.html'
    context_object_name = 'claim'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['line_items'] = self.object.line_items.all()
        from django.contrib.auth.models import User
        context['users'] = User.objects.all()
        context['notes'] = self.object.claim_notes.all()
        context['edi_logs'] = self.object.edi_transmissions.all()
        
        # Get rejection codes and their descriptions
        from reference_data.models import RejectionCode
        rejection_codes = self.object.line_items.exclude(rejection_code='').values_list('rejection_code', flat=True).distinct()
        if rejection_codes:
            context['rejection_reasons'] = RejectionCode.objects.filter(code__in=rejection_codes)
        else:
            context['rejection_reasons'] = []
        return context

class ClaimCreateView(LoginRequiredMixin, CreateView):
    model = Claim
    form_class = ClaimForm
    template_name = 'claims/claim_form.html'
    
    def get_success_url(self):
        return reverse_lazy('claims:detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = ClaimLineItemFormSet(self.request.POST)
        else:
            context['formset'] = ClaimLineItemFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        
        if formset.is_valid():
            self.object = form.save(commit=False)
            self.object.created_by = self.request.user
            self.object.save()
            formset.instance = self.object
            formset.save()
            messages.success(self.request, "Claim created successfully.")
            return redirect('claims:detail', pk=self.object.pk)
        else:
            return self.form_invalid(form)

class ClaimUpdateView(LoginRequiredMixin, UpdateView):
    model = Claim
    form_class = ClaimForm
    template_name = 'claims/claim_form.html'

    def get_success_url(self):
        return reverse_lazy('claims:detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = ClaimLineItemFormSet(self.request.POST, instance=self.object)
        else:
            context['formset'] = ClaimLineItemFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        
        if formset.is_valid():
            self.object = form.save()
            formset.save()
            messages.success(self.request, "Claim updated successfully.")
            return redirect('claims:detail', pk=self.object.pk)
        else:
            return self.form_invalid(form)

class ClaimDeleteView(LoginRequiredMixin, DeleteView):
    model = Claim
    template_name = 'claims/claim_confirm_delete.html'
    success_url = reverse_lazy('claims:list')

    def form_valid(self, form):
        claim_id = self.object.id
        response = super().form_valid(form)
        messages.success(self.request, f"Claim #{claim_id} deleted successfully.")
        return response

@require_POST
@login_required
def claim_submit(request, pk):
    claim = get_object_or_404(Claim, pk=pk)
    if claim.claim_status == 'draft':
        claim.claim_status = 'submitted'
        claim.submission_date = timezone.now().date()
        claim.save()
        messages.success(request, f"Claim {claim.id} has been submitted.")
    else:
        messages.error(request, f"Claim {claim.id} cannot be submitted as it is not in draft status.")
    
    return redirect('claims:detail', pk=pk)

@require_POST
@login_required
def claim_edi_submit(request, pk):
    claim = get_object_or_404(Claim, pk=pk)
    from .tasks import batch_claims_edi
    res = batch_claims_edi(claim_id=claim.id)
    if res.get('success'):
        messages.success(
            request,
            f"Medclaim EDI submission processed. Batch Ref: {res.get('batch_reference')} (Status: {res.get('status', 'ACCEPTED').upper()})."
        )
    else:
        messages.warning(request, f"EDI submission failed: {res.get('message', 'Check pre-scrubbing rules.')}")
    return redirect('claims:detail', pk=pk)


@require_POST
@login_required
def claim_add_note(request, pk):
    claim = get_object_or_404(Claim, pk=pk)
    text = request.POST.get('text')
    if text:
        from .models import ClaimNote
        ClaimNote.objects.create(claim=claim, author=request.user, text=text)
        messages.success(request, "Note added.")
    return redirect('claims:detail', pk=pk)

import json
from django.http import JsonResponse
from django.views.generic import TemplateView







