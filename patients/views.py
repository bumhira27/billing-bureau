from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.db.models import Q, F, Sum
from .models import Patient, PatientScheme
from .forms import PatientForm, PatientSchemeForm
from practices.models import Practice

class CreatedByMixin:
    def form_valid(self, form):
        if hasattr(form.instance, 'created_by_id') and not form.instance.created_by_id:
            form.instance.created_by = self.request.user
        return super().form_valid(form)

class PatientListView(ListView):
    model = Patient
    paginate_by = 30
    context_object_name = 'patients'
    
    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return ['patients/patient_list_partial.html']
        return ['patients/patient_list.html']

    def get_queryset(self):
        qs = super().get_queryset()
        practice_id = self.request.GET.get('practice')
        q = self.request.GET.get('q')
        
        if practice_id:
            qs = qs.filter(practice_id=practice_id)
        if q:
            qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(id_number__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['practices'] = Practice.objects.all()
        return context

class PatientDetailView(DetailView):
    model = Patient
    template_name = 'patients/patient_detail.html'
    context_object_name = 'patient'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['schemes'] = self.object.schemes.all()
        claims = self.object.claims.all().order_by('-date_of_service', '-created_at')
        context['claims'] = claims
        outstanding_agg = claims.annotate(
            bal=F('total_billed') - F('total_paid')
        ).filter(bal__gt=0).aggregate(total=Sum('bal'))['total'] or 0
        context['outstanding_balance'] = round(float(outstanding_agg), 2)
        return context

class PatientCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = Patient
    form_class = PatientForm
    template_name = 'patients/patient_form.html'

    def get_initial(self):
        initial = super().get_initial()
        initial['practice'] = self.kwargs.get('practice_id')
        return initial

    def get_success_url(self):
        return reverse_lazy('patients:detail', kwargs={'pk': self.object.pk})

class PatientUpdateView(LoginRequiredMixin, UpdateView):
    model = Patient
    form_class = PatientForm
    template_name = 'patients/patient_form.html'

    def get_success_url(self):
        return reverse_lazy('patients:detail', kwargs={'pk': self.object.pk})

class PatientSchemeCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = PatientScheme
    form_class = PatientSchemeForm
    template_name = 'patients/patientscheme_form.html'

    def get_initial(self):
        initial = super().get_initial()
        initial['patient'] = self.kwargs.get('patient_id')
        return initial

    def get_success_url(self):
        return reverse_lazy('patients:detail', kwargs={'pk': self.kwargs.get('patient_id')})

def patient_search_api(request):
    q = request.GET.get('q', '')
    practice_id = request.GET.get('practice', '')
    
    qs = Patient.objects.all()
    if q:
        qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(id_number__icontains=q))
    if practice_id:
        qs = qs.filter(practice_id=practice_id)
        
    qs = qs[:15]
    
    data = []
    for p in qs:
        scheme = p.active_scheme
        scheme_info = str(scheme) if scheme else "No Active Scheme"
        data.append({
            'id': p.id,
            'full_name': p.full_name,
            'id_number': p.id_number,
            'scheme_info': scheme_info
        })
        
    return JsonResponse(data, safe=False)
