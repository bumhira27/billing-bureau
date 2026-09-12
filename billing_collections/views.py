from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, ListView, DetailView, CreateView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.db.models import Sum, Count, F, Q
from django.utils import timezone

from .models import PatientStatement, Payment
from .forms import PaymentForm, GenerateStatementForm
from practices.models import Practice
from patients.models import Patient
from claims.models import Claim

class CollectionsOverviewView(LoginRequiredMixin, TemplateView):
    template_name = 'billing_collections/overview.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        
        # This assumes Claim model has total_billed and total_paid fields
        claims = Claim.objects.annotate(outstanding=F('total_billed') - F('total_paid')).filter(outstanding__gt=0)
        total_outstanding = round(float(claims.aggregate(total=Sum('outstanding'))['total'] or 0), 2)
        patients_with_balances = claims.values('patient').distinct().count()
        
        statements_this_month = PatientStatement.objects.filter(statement_date__month=now.month, statement_date__year=now.year).count()
        payments_this_month = round(float(Payment.objects.filter(payment_date__month=now.month, payment_date__year=now.year).aggregate(total=Sum('amount'))['total'] or 0), 2)

        context['total_outstanding'] = total_outstanding
        context['patients_with_balances'] = patients_with_balances
        context['statements_this_month'] = statements_this_month
        context['payments_this_month'] = payments_this_month
        
        context['recent_payments'] = Payment.objects.order_by('-payment_date', '-created_at')[:15]
        context['recent_statements'] = PatientStatement.objects.order_by('-statement_date', '-created_at')[:10]
        
        return context

class StatementListView(LoginRequiredMixin, ListView):
    model = PatientStatement
    template_name = 'billing_collections/patientstatement_list.html'
    context_object_name = 'statements'
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset()
        practice_id = self.request.GET.get('practice')
        delivery_status = self.request.GET.get('delivery_status')
        
        if practice_id:
            qs = qs.filter(practice_id=practice_id)
        if delivery_status:
            qs = qs.filter(delivery_status=delivery_status)
            
        return qs

def generate_statements_view(request):
    if request.method == 'POST':
        form = GenerateStatementForm(request.POST)
        if form.is_valid():
            practice = form.cleaned_data['practice']
            as_of_date = form.cleaned_data['as_of_date']
            min_outstanding = form.cleaned_data['min_outstanding']
            send_via = form.cleaned_data['send_via']
            
            # Find patients with outstanding claims in this practice
            # Assuming Claim has total_billed and total_paid
            claims = Claim.objects.filter(practice=practice).annotate(
                outstanding=F('total_billed') - F('total_paid')
            ).filter(outstanding__gt=0, date_of_service__lte=as_of_date)
            
            patient_claims_map = {}
            for claim in claims:
                if claim.patient not in patient_claims_map:
                    patient_claims_map[claim.patient] = []
                patient_claims_map[claim.patient].append(claim)
            
            count = 0
            for patient, p_claims in patient_claims_map.items():
                total_outstanding = sum(c.outstanding for c in p_claims)
                
                if total_outstanding >= min_outstanding:
                    statement = PatientStatement.objects.create(
                        patient=patient,
                        practice=practice,
                        total_outstanding=total_outstanding,
                        sent_via=send_via,
                        delivery_status='pending' if send_via else 'not_sent',
                        message_content=f"Dear {patient}, you have an outstanding balance of R {total_outstanding:,.2f} for services rendered at {practice}. Please contact us to arrange payment."
                    )
                    statement.message_content += f" Reference: {statement.id}"
                    statement.save()
                    statement.claims_included.set(p_claims)
                    count += 1
            
            messages.success(request, f'Successfully generated {count} statements.')
            return redirect('billing_collections:statement_list')
    else:
        form = GenerateStatementForm()
        
    return render(request, 'billing_collections/generate_statements.html', {'form': form})

class StatementDetailView(LoginRequiredMixin, DetailView):
    model = PatientStatement
    template_name = 'billing_collections/patientstatement_detail.html'
    context_object_name = 'statement'

class PaymentListView(LoginRequiredMixin, ListView):
    model = Payment
    template_name = 'billing_collections/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 30

    def get_queryset(self):
        qs = super().get_queryset()
        practice_id = self.request.GET.get('practice')
        payment_source = self.request.GET.get('payment_source')
        
        if practice_id:
            qs = qs.filter(claim__practice_id=practice_id)
        if payment_source:
            qs = qs.filter(payment_source=payment_source)
            
        return qs

class PaymentCreateView(LoginRequiredMixin, CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'billing_collections/payment_form.html'
    
    def get_success_url(self):
        return reverse('claims:claim_detail', kwargs={'pk': self.object.claim.pk})
        
    def form_valid(self, form):
        messages.success(self.request, 'Payment successfully recorded.')
        return super().form_valid(form)

def patient_balance_api(request):
    patient_id = request.GET.get('patient_id')
    if not patient_id:
        return JsonResponse({'error': 'patient_id is required'}, status=400)
        
    claims = Claim.objects.filter(patient_id=patient_id).annotate(
        outstanding=F('total_billed') - F('total_paid')
    ).filter(outstanding__gt=0)
    
    data = []
    total = 0
    for c in claims:
        data.append({
            'claim_id': c.id,
            'practice': str(c.practice),
            'date_of_service': c.date_of_service.isoformat() if c.date_of_service else None,
            'outstanding': f"{round(float(c.outstanding), 2):.2f}"
        })
        total += c.outstanding
        
    return JsonResponse({'total_outstanding': f"{round(float(total), 2):.2f}", 'claims': data})
