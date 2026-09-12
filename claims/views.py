from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .models import Claim, ClaimLineItem
from .forms import ClaimForm, ClaimLineItemFormSet, NoteUploadForm
from .services.ai_extractor import extract_from_image
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

class ClaimListView(LoginRequiredMixin, ListView):
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

class ClaimDetailView(LoginRequiredMixin, DetailView):
    model = Claim
    template_name = 'claims/claim_detail.html'
    context_object_name = 'claim'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['line_items'] = self.object.line_items.all()
        from django.contrib.auth.models import User
        context['users'] = User.objects.all()
        context['notes'] = self.object.claim_notes.all()
        context['rpa_logs'] = self.object.rpa_submissions.all()
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
def claim_rpa_submit(request, pk):
    claim = get_object_or_404(Claim, pk=pk)
    from .tasks import submit_claim_rpa
    res = submit_claim_rpa(claim.id)
    if res.get('success'):
        messages.success(request, f"Direct Portal Submission Successful! Reference: {res.get('reference_number')} on {res.get('portal')} (Duration: {res.get('execution_time')}s).")
    else:
        messages.warning(request, f"Portal submission result: {res.get('error', 'Check audit logs')}")
    return redirect('claims:detail', pk=pk)

@require_POST
@login_required
def claim_assign(request, pk):
    claim = get_object_or_404(Claim, pk=pk)
    assigned_to_id = request.POST.get('assigned_to')
    internal_priority = request.POST.get('internal_priority')
    
    if assigned_to_id:
        from django.contrib.auth.models import User
        claim.assigned_to = get_object_or_404(User, pk=assigned_to_id)
    else:
        claim.assigned_to = None
        
    if internal_priority in [c[0] for c in Claim.PRIORITY_CHOICES]:
        claim.internal_priority = internal_priority
        
    claim.save()
    messages.success(request, "Claim assignment updated.")
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

class BatchCaptureView(LoginRequiredMixin, TemplateView):
    template_name = 'claims/batch_capture.html'
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            rows = data.get('rows', [])
            
            from practices.models import Practice
            practice = Practice.objects.first()
            if not practice:
                return JsonResponse({"error": "No practice found. Please create one first."}, status=400)
            
            from patients.models import Patient
            created_count = 0
            for row in rows:
                service_date = row.get('service_date')
                patient_id = row.get('patient_id')
                tariff_code = row.get('tariff_code')
                icd10 = row.get('icd10')
                quantity = int(row.get('quantity') or 1)
                billed_amount = row.get('billed_amount')
                
                if not all([service_date, patient_id, tariff_code, icd10, billed_amount]):
                    continue
                
                patient = Patient.objects.filter(id=patient_id).first()
                if not patient:
                    continue
                    
                claim = Claim.objects.create(
                    practice=practice,
                    patient=patient,
                    date_of_service=service_date,
                    claim_status='draft',
                    source_type='manual'
                )
                
                ClaimLineItem.objects.create(
                    claim=claim,
                    tariff_code=tariff_code,
                    icd10_primary=icd10,
                    quantity=quantity,
                    amount_billed=billed_amount
                )
                claim.recalculate_totals()
                created_count += 1
            
            return JsonResponse({"status": "success", "message": f"{created_count} claims created."})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


from django.views.generic.edit import FormView

class UploadNoteView(LoginRequiredMixin, FormView):
    template_name = 'claims/upload_note.html'
    form_class = NoteUploadForm

    def form_valid(self, form):
        practice = form.cleaned_data['practice']
        note_file = form.cleaned_data['note_file']
        instructions = form.cleaned_data.get('notes', '')

        first_patient = practice.patients.first()
        if not first_patient:
            from patients.models import Patient
            first_patient = Patient.objects.create(
                practice=practice,
                first_name="Unassigned",
                last_name="Patient",
                date_of_birth=date(1990, 1, 1),
                gender="O"
            )

        claim = Claim.objects.create(
            practice=practice,
            patient=first_patient,
            source_type='photo',
            source_file=note_file,
            claim_status='draft',
            created_by=self.request.user,
            notes=instructions,
            date_of_service=timezone.now().date(),
        )

        try:
            image_path = claim.source_file.path
            extraction = extract_from_image(image_path)

            if extraction.patient_name:
                parts = extraction.patient_name.strip().split()
                if len(parts) >= 2:
                    matched_pt = practice.patients.filter(
                        first_name__icontains=parts[0], 
                        last_name__icontains=parts[-1]
                    ).first()
                    if matched_pt:
                        claim.patient = matched_pt
                elif len(parts) == 1:
                    matched_pt = practice.patients.filter(
                        Q(first_name__icontains=parts[0]) | Q(last_name__icontains=parts[0])
                    ).first()
                    if matched_pt:
                        claim.patient = matched_pt

            if extraction.date_of_service:
                try:
                    claim.date_of_service = datetime.strptime(extraction.date_of_service, "%Y-%m-%d").date()
                except ValueError:
                    pass

            if extraction.referring_doctor:
                claim.referring_doctor_name = extraction.referring_doctor
            if extraction.authorization_number:
                claim.authorization_number = extraction.authorization_number

            if extraction.clinical_notes:
                notes_text = f"Clinical Transcription:\n{extraction.clinical_notes}"
                claim.notes = f"{claim.notes}\n\n{notes_text}".strip() if claim.notes else notes_text

            claim.save()

            for item in extraction.line_items:
                ClaimLineItem.objects.create(
                    claim=claim,
                    tariff_code=item.tariff_code,
                    tariff_description=item.tariff_description,
                    icd10_primary=item.icd10_code,
                    quantity=item.quantity,
                    amount_billed=item.billed_amount
                )

            claim.recalculate_totals()
            messages.success(self.request, "Handwritten note analyzed. Review and confirm the extracted billing details.")
        except Exception as e:
            logger.error(f"Error during note extraction: {e}")
            messages.warning(self.request, f"Note uploaded, but extraction had an error: {e}")

        return redirect('claims:review_extracted', pk=claim.pk)


class ReviewExtractedClaimView(LoginRequiredMixin, UpdateView):
    model = Claim
    form_class = ClaimForm
    template_name = 'claims/review_extracted_claim.html'

    def get_success_url(self):
        return reverse_lazy('claims:detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = ClaimLineItemFormSet(self.request.POST, instance=self.object)
        else:
            context['formset'] = ClaimLineItemFormSet(instance=self.object)
        context['practice_patients'] = self.object.practice.patients.all()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        if formset.is_valid():
            self.object = form.save(commit=False)
            action = self.request.POST.get('action', 'save_draft')
            if action == 'submit':
                self.object.claim_status = 'submitted'
                self.object.submission_date = timezone.now().date()
                messages.success(self.request, f"Claim {self.object.id} verified and submitted successfully.")
            else:
                self.object.claim_status = 'draft'
                messages.success(self.request, f"Claim {self.object.id} saved as draft.")
            self.object.save()
            formset.save()
            self.object.recalculate_totals()
            return redirect('claims:detail', pk=self.object.pk)
        else:
            return self.form_invalid(form)

