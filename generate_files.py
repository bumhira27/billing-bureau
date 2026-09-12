import os

base_dir = r"c:\Users\bumhira27\Desktop\Billing Bureau"
practices_dir = os.path.join(base_dir, "practices")
patients_dir = os.path.join(base_dir, "patients")

def make_dirs(path):
    if not os.path.exists(path):
        os.makedirs(path)

make_dirs(os.path.join(practices_dir, "templates", "practices"))
make_dirs(os.path.join(patients_dir, "templates", "patients"))

def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

# PRACTICES APP
write_file(os.path.join(practices_dir, "__init__.py"), "")

practices_models = """from django.db import models
from core.models import TimeStampedModel

class Practice(TimeStampedModel):
    SWITCH_CHOICES = [
        ('mediswitch', 'MediSwitch'),
        ('healthbridge', 'Healthbridge'),
        ('medikredit', 'MediKredit'),
        ('none', 'None')
    ]
    FEE_TYPE_CHOICES = [
        ('percentage', 'Percentage of Collections'),
        ('fixed', 'Fixed Monthly Fee'),
        ('hybrid', 'Hybrid (Fixed + Percentage)')
    ]

    practice_name = models.CharField(max_length=255)
    bhf_practice_number = models.CharField(max_length=20, unique=True, help_text='Board of Healthcare Funders practice number')
    hpcsa_number = models.CharField(max_length=20, help_text='HPCSA registration number')
    owner_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    physical_address = models.TextField(blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account_number = models.CharField(max_length=30, blank=True)
    bank_branch_code = models.CharField(max_length=10, blank=True)
    switch_provider = models.CharField(max_length=20, choices=SWITCH_CHOICES, default='none')
    switch_account_id = models.CharField(max_length=50, blank=True)
    fee_type = models.CharField(max_length=20, choices=FEE_TYPE_CHOICES, default='percentage')
    fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=7.00, help_text='Percentage fee on collected revenue')
    fee_fixed_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Fixed monthly fee in Rands')
    popia_agreement_signed_date = models.DateField(null=True, blank=True)
    service_agreement_signed_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['practice_name']
        verbose_name = 'Practice'
        verbose_name_plural = 'Practices'

    def __str__(self):
        return self.practice_name

    @property
    def is_compliant(self):
        return bool(self.popia_agreement_signed_date and self.service_agreement_signed_date)
"""
write_file(os.path.join(practices_dir, "models.py"), practices_models)

practices_forms = """from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, Row, Column
from .models import Practice

class PracticeForm(forms.ModelForm):
    class Meta:
        model = Practice
        exclude = ['created_by']
        widgets = {
            'popia_agreement_signed_date': forms.DateInput(attrs={'type': 'date'}),
            'service_agreement_signed_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset(
                'Practice Details',
                Row(
                    Column('practice_name', css_class='form-group col-md-6 mb-0'),
                    Column('owner_name', css_class='form-group col-md-6 mb-0'),
                    css_class='form-row'
                ),
                Row(
                    Column('bhf_practice_number', css_class='form-group col-md-6 mb-0'),
                    Column('hpcsa_number', css_class='form-group col-md-6 mb-0'),
                    css_class='form-row'
                )
            ),
            Fieldset(
                'Contact',
                Row(
                    Column('phone', css_class='form-group col-md-6 mb-0'),
                    Column('email', css_class='form-group col-md-6 mb-0'),
                    css_class='form-row'
                ),
                'physical_address',
                'postal_code'
            ),
            Fieldset(
                'Banking',
                Row(
                    Column('bank_name', css_class='form-group col-md-4 mb-0'),
                    Column('bank_account_number', css_class='form-group col-md-4 mb-0'),
                    Column('bank_branch_code', css_class='form-group col-md-4 mb-0'),
                    css_class='form-row'
                )
            ),
            Fieldset(
                'Switch Integration',
                Row(
                    Column('switch_provider', css_class='form-group col-md-6 mb-0'),
                    Column('switch_account_id', css_class='form-group col-md-6 mb-0'),
                    css_class='form-row'
                )
            ),
            Fieldset(
                'Fee Structure',
                Row(
                    Column('fee_type', css_class='form-group col-md-4 mb-0'),
                    Column('fee_percentage', css_class='form-group col-md-4 mb-0'),
                    Column('fee_fixed_amount', css_class='form-group col-md-4 mb-0'),
                    css_class='form-row'
                )
            ),
            Fieldset(
                'Compliance',
                Row(
                    Column('popia_agreement_signed_date', css_class='form-group col-md-6 mb-0'),
                    Column('service_agreement_signed_date', css_class='form-group col-md-6 mb-0'),
                    css_class='form-row'
                ),
                'is_active'
            )
        )
"""
write_file(os.path.join(practices_dir, "forms.py"), practices_forms)

practices_views = """from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from .models import Practice
from .forms import PracticeForm

class CreatedByMixin:
    def form_valid(self, form):
        if hasattr(form.instance, 'created_by_id') and not form.instance.created_by_id:
            form.instance.created_by = self.request.user
        return super().form_valid(form)

class PracticeListView(ListView):
    model = Practice
    template_name = 'practices/practice_list.html'
    context_object_name = 'practices'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(Q(practice_name__icontains=q) | Q(bhf_practice_number__icontains=q))
        return qs

class PracticeDetailView(DetailView):
    model = Practice
    template_name = 'practices/practice_detail.html'
    context_object_name = 'practice'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Mock values as models don't exist yet
        context['recent_claims_count'] = 0
        context['total_collections'] = 0.0
        return context

class PracticeCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = Practice
    form_class = PracticeForm
    template_name = 'practices/practice_form.html'
    success_url = reverse_lazy('practices:list')

class PracticeUpdateView(LoginRequiredMixin, UpdateView):
    model = Practice
    form_class = PracticeForm
    template_name = 'practices/practice_form.html'
    
    def get_success_url(self):
        return reverse_lazy('practices:detail', kwargs={'pk': self.object.pk})
"""
write_file(os.path.join(practices_dir, "views.py"), practices_views)

practices_urls = """from django.urls import path
from . import views

app_name = 'practices'

urlpatterns = [
    path('', views.PracticeListView.as_view(), name='list'),
    path('create/', views.PracticeCreateView.as_view(), name='create'),
    path('<int:pk>/', views.PracticeDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.PracticeUpdateView.as_view(), name='update'),
]
"""
write_file(os.path.join(practices_dir, "urls.py"), practices_urls)

practices_admin = """from django.contrib import admin
from .models import Practice

@admin.register(Practice)
class PracticeAdmin(admin.ModelAdmin):
    list_display = ['practice_name', 'bhf_practice_number', 'owner_name', 'phone', 'is_active', 'switch_provider']
    list_filter = ['is_active', 'switch_provider', 'fee_type']
    search_fields = ['practice_name', 'bhf_practice_number', 'owner_name']
"""
write_file(os.path.join(practices_dir, "admin.py"), practices_admin)

practices_list_html = """{% extends 'base.html' %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h2>Practices</h2>
    <a href="{% url 'practices:create' %}" class="btn btn-primary">Add Practice</a>
</div>

<form method="get" class="mb-4">
    <div class="input-group">
        <input type="text" name="q" class="form-control" placeholder="Search practices..." value="{{ request.GET.q }}">
        <button class="btn btn-outline-secondary" type="submit">Search</button>
    </div>
</form>

{% if practices %}
<div class="table-responsive">
    <table class="table table-striped table-hover">
        <thead>
            <tr>
                <th>Practice Name</th>
                <th>BHF Number</th>
                <th>Owner</th>
                <th>Phone</th>
                <th>Status</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for practice in practices %}
            <tr>
                <td>{{ practice.practice_name }}</td>
                <td>{{ practice.bhf_practice_number }}</td>
                <td>{{ practice.owner_name }}</td>
                <td>{{ practice.phone }}</td>
                <td>
                    {% if practice.is_active %}
                        <span class="badge bg-success">Active</span>
                    {% else %}
                        <span class="badge bg-secondary">Inactive</span>
                    {% endif %}
                </td>
                <td>
                    <a href="{% url 'practices:detail' practice.pk %}" class="btn btn-sm btn-info">View</a>
                    <a href="{% url 'practices:update' practice.pk %}" class="btn btn-sm btn-warning">Edit</a>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% include 'pagination.html' %}
{% else %}
<div class="alert alert-info">No practices found.</div>
{% endif %}
{% endblock %}
"""
write_file(os.path.join(practices_dir, "templates", "practices", "practice_list.html"), practices_list_html)

practices_detail_html = """{% extends 'base.html' %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h2>{{ practice.practice_name }}</h2>
    <a href="{% url 'practices:update' practice.pk %}" class="btn btn-warning">Edit Practice</a>
</div>

{% if practice.is_compliant %}
    <div class="alert alert-success">Compliance: Fully Compliant</div>
{% else %}
    <div class="alert alert-warning">Compliance: Missing Agreements</div>
{% endif %}

<div class="row">
    <div class="col-md-8">
        <div class="card mb-4">
            <div class="card-header">Practice Details</div>
            <div class="card-body">
                <p><strong>Owner:</strong> {{ practice.owner_name }}</p>
                <p><strong>BHF Number:</strong> {{ practice.bhf_practice_number }}</p>
                <p><strong>HPCSA Number:</strong> {{ practice.hpcsa_number }}</p>
                <p><strong>Phone:</strong> {{ practice.phone }}</p>
                <p><strong>Email:</strong> {{ practice.email }}</p>
                <p><strong>Address:</strong> {{ practice.physical_address }} {{ practice.postal_code }}</p>
                <p><strong>Switch Provider:</strong> {{ practice.get_switch_provider_display }}</p>
                <p><strong>Switch Account ID:</strong> {{ practice.switch_account_id }}</p>
                <p><strong>Fee Type:</strong> {{ practice.get_fee_type_display }}</p>
                <p><strong>Banking:</strong> {{ practice.bank_name }} - {{ practice.bank_account_number }}</p>
            </div>
        </div>
    </div>
    
    <div class="col-md-4">
        <div class="card mb-4">
            <div class="card-header">Quick Stats</div>
            <div class="card-body">
                <p><strong>Recent Claims:</strong> {{ recent_claims_count }}</p>
                <p><strong>Total Billed:</strong> R 0.00</p>
                <p><strong>Total Collected:</strong> R {{ total_collections }}</p>
                <p><strong>Collection Rate:</strong> 0%</p>
            </div>
        </div>
    </div>
</div>

<div class="card">
    <div class="card-header">Recent Claims</div>
    <div class="card-body">
        <p>No recent claims found.</p>
    </div>
</div>
{% endblock %}
"""
write_file(os.path.join(practices_dir, "templates", "practices", "practice_detail.html"), practices_detail_html)

practices_form_html = """{% extends 'base.html' %}
{% load crispy_forms_tags %}

{% block content %}
<h2>{% if form.instance.pk %}Edit Practice{% else %}Add Practice{% endif %}</h2>
<div class="card">
    <div class="card-body">
        {% crispy form %}
        <a href="{% url 'practices:list' %}" class="btn btn-secondary mt-3">Cancel</a>
    </div>
</div>
{% endblock %}
"""
write_file(os.path.join(practices_dir, "templates", "practices", "practice_form.html"), practices_form_html)


# PATIENTS APP
write_file(os.path.join(patients_dir, "__init__.py"), "")

patients_models = """from django.db import models
from django.core.validators import RegexValidator
from core.models import TimeStampedModel
from practices.models import Practice

class Patient(TimeStampedModel):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    practice = models.ForeignKey(Practice, on_delete=models.CASCADE, related_name='patients')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    id_number = models.CharField(
        max_length=13, 
        blank=True, 
        help_text='SA ID number',
        validators=[RegexValidator(r'^\d{13}$', 'Enter a valid 13-digit SA ID number.')]
    )
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    physical_address = models.TextField(blank=True)
    postal_code = models.CharField(max_length=10, blank=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        unique_together = [['practice', 'id_number']]
        verbose_name = 'Patient'
        verbose_name_plural = 'Patients'

    def __str__(self):
        return f"{self.last_name}, {self.first_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def active_scheme(self):
        return self.schemes.filter(is_active=True).first()


class PatientScheme(TimeStampedModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='schemes')
    scheme_name = models.CharField(max_length=255)
    scheme_option = models.CharField(max_length=100, blank=True)
    membership_number = models.CharField(max_length=50)
    dependent_code = models.CharField(max_length=5, default='00')
    main_member_name = models.CharField(max_length=255, blank=True)
    main_member_id_number = models.CharField(max_length=13, blank=True)
    is_active = models.BooleanField(default=True)
    verified_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-is_active', 'scheme_name']
        verbose_name = 'Patient Scheme'
        verbose_name_plural = 'Patient Schemes'

    def __str__(self):
        return f"{self.scheme_name} - {self.membership_number} (dep {self.dependent_code})"
"""
write_file(os.path.join(patients_dir, "models.py"), patients_models)

patients_forms = """from django import forms
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
"""
write_file(os.path.join(patients_dir, "forms.py"), patients_forms)

patients_views = """from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Q
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
        context['recent_claims'] = []
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
"""
write_file(os.path.join(patients_dir, "views.py"), patients_views)

patients_urls = """from django.urls import path
from . import views

app_name = 'patients'

urlpatterns = [
    path('', views.PatientListView.as_view(), name='list'),
    path('create/<int:practice_id>/', views.PatientCreateView.as_view(), name='create'),
    path('<int:pk>/', views.PatientDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.PatientUpdateView.as_view(), name='update'),
    path('<int:patient_id>/scheme/add/', views.PatientSchemeCreateView.as_view(), name='add_scheme'),
    path('search/', views.patient_search_api, name='search_api'),
]
"""
write_file(os.path.join(patients_dir, "urls.py"), patients_urls)

patients_admin = """from django.contrib import admin
from .models import Patient, PatientScheme

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'id_number', 'practice', 'phone']
    list_filter = ['practice', 'gender']
    search_fields = ['first_name', 'last_name', 'id_number']

@admin.register(PatientScheme)
class PatientSchemeAdmin(admin.ModelAdmin):
    list_display = ['patient', 'scheme_name', 'membership_number', 'dependent_code', 'is_active']
    list_filter = ['scheme_name', 'is_active']
    search_fields = ['patient__first_name', 'patient__last_name', 'scheme_name', 'membership_number']
"""
write_file(os.path.join(patients_dir, "admin.py"), patients_admin)

patients_list_html = """{% extends 'base.html' %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h2>Patients</h2>
    <div class="dropdown">
        <button class="btn btn-primary dropdown-toggle" type="button" id="addPatientDropdown" data-bs-toggle="dropdown" aria-expanded="false">
            Add Patient
        </button>
        <ul class="dropdown-menu" aria-labelledby="addPatientDropdown">
            {% for p in practices %}
                <li><a class="dropdown-item" href="{% url 'patients:create' p.pk %}">{{ p.practice_name }}</a></li>
            {% endfor %}
        </ul>
    </div>
</div>

<form method="get" class="mb-4 row" hx-get="{% url 'patients:list' %}" hx-target="#patient-table-body" hx-trigger="keyup from:[name='q'] delay:500ms, change from:[name='practice']">
    <div class="col-md-8">
        <input type="text" name="q" class="form-control" placeholder="Search patients..." value="{{ request.GET.q }}">
    </div>
    <div class="col-md-4">
        <select name="practice" class="form-control">
            <option value="">All Practices</option>
            {% for p in practices %}
                <option value="{{ p.id }}" {% if request.GET.practice == p.id|stringformat:"s" %}selected{% endif %}>{{ p.practice_name }}</option>
            {% endfor %}
        </select>
    </div>
</form>

<div class="table-responsive">
    <table class="table table-striped table-hover">
        <thead>
            <tr>
                <th>Name</th>
                <th>ID Number</th>
                <th>Scheme</th>
                <th>Phone</th>
                <th>Practice</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody id="patient-table-body">
            {% include 'patients/patient_list_partial.html' %}
        </tbody>
    </table>
</div>

{% include 'pagination.html' %}
{% endblock %}
"""
write_file(os.path.join(patients_dir, "templates", "patients", "patient_list.html"), patients_list_html)

patients_detail_html = """{% extends 'base.html' %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h2>{{ patient.full_name }}</h2>
    <a href="{% url 'patients:update' patient.pk %}" class="btn btn-warning">Edit Patient</a>
</div>

<div class="row">
    <div class="col-md-6">
        <div class="card mb-4">
            <div class="card-header">Personal Details</div>
            <div class="card-body">
                <p><strong>Practice:</strong> {{ patient.practice.practice_name }}</p>
                <p><strong>ID Number:</strong> {{ patient.id_number }}</p>
                <p><strong>Date of Birth:</strong> {{ patient.date_of_birth }}</p>
                <p><strong>Gender:</strong> {{ patient.get_gender_display }}</p>
                <p><strong>Phone:</strong> {{ patient.phone }}</p>
                <p><strong>Email:</strong> {{ patient.email }}</p>
                <p><strong>Address:</strong> {{ patient.physical_address }} {{ patient.postal_code }}</p>
            </div>
        </div>
    </div>
    <div class="col-md-6">
        <div class="card mb-4">
            <div class="card-header d-flex justify-content-between align-items-center">
                <span>Scheme Memberships</span>
                <a href="{% url 'patients:add_scheme' patient.pk %}" class="btn btn-sm btn-primary">Add Scheme</a>
            </div>
            <div class="card-body">
                {% if schemes %}
                    <ul class="list-group">
                    {% for scheme in schemes %}
                        <li class="list-group-item">
                            <strong>{{ scheme.scheme_name }}</strong> - {{ scheme.membership_number }}
                            {% if scheme.is_active %}<span class="badge bg-success float-end">Active</span>{% else %}<span class="badge bg-secondary float-end">Inactive</span>{% endif %}
                        </li>
                    {% endfor %}
                    </ul>
                {% else %}
                    <p>No schemes recorded.</p>
                {% endif %}
            </div>
        </div>
        
        <div class="card mb-4">
            <div class="card-header">Outstanding Balance</div>
            <div class="card-body">
                <p class="fs-4 text-danger">R 0.00</p>
            </div>
        </div>
    </div>
</div>

<div class="card">
    <div class="card-header">Claims History</div>
    <div class="card-body">
        <p>No claims found.</p>
    </div>
</div>
{% endblock %}
"""
write_file(os.path.join(patients_dir, "templates", "patients", "patient_detail.html"), patients_detail_html)

patient_form_html = """{% extends 'base.html' %}
{% load crispy_forms_tags %}

{% block content %}
<h2>{% if form.instance.pk %}Edit Patient{% else %}Add Patient{% endif %}</h2>
<div class="card">
    <div class="card-body">
        {% crispy form %}
        <a href="{% if form.instance.pk %}{% url 'patients:detail' form.instance.pk %}{% else %}{% url 'patients:list' %}{% endif %}" class="btn btn-secondary mt-3">Cancel</a>
    </div>
</div>
{% endblock %}
"""
write_file(os.path.join(patients_dir, "templates", "patients", "patient_form.html"), patient_form_html)

patientscheme_form_html = """{% extends 'base.html' %}
{% load crispy_forms_tags %}

{% block content %}
<h2>Add Scheme for {{ view.kwargs.patient_id }}</h2>
<div class="card">
    <div class="card-body">
        {% crispy form %}
        <a href="{% url 'patients:detail' view.kwargs.patient_id %}" class="btn btn-secondary mt-3">Cancel</a>
    </div>
</div>
{% endblock %}
"""
write_file(os.path.join(patients_dir, "templates", "patients", "patientscheme_form.html"), patientscheme_form_html)

patient_list_partial_html = """{% for patient in patients %}
<tr>
    <td>{{ patient.full_name }}</td>
    <td>{{ patient.id_number }}</td>
    <td>
        {% if patient.active_scheme %}
            {{ patient.active_scheme.scheme_name }}
        {% else %}
            <span class="text-muted">None</span>
        {% endif %}
    </td>
    <td>{{ patient.phone }}</td>
    <td>{{ patient.practice.practice_name }}</td>
    <td>
        <a href="{% url 'patients:detail' patient.pk %}" class="btn btn-sm btn-info">View</a>
        <a href="{% url 'patients:update' patient.pk %}" class="btn btn-sm btn-warning">Edit</a>
    </td>
</tr>
{% empty %}
<tr>
    <td colspan="6" class="text-center">No patients found.</td>
</tr>
{% endfor %}
"""
write_file(os.path.join(patients_dir, "templates", "patients", "patient_list_partial.html"), patient_list_partial_html)

print("Files generated successfully.")
