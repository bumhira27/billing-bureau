import os

base_dir = r"c:\Users\bumhira27\Desktop\Billing Bureau\reconciliation"

dirs = [
    "",
    "parsers",
    "templates",
    "templates/reconciliation"
]

for d in dirs:
    os.makedirs(os.path.join(base_dir, d), exist_ok=True)

files = {}

files["__init__.py"] = ""

files["parsers/__init__.py"] = ""

files["models.py"] = """from django.db import models
from django.db.models import JSONField
from core.models import TimeStampedModel

class RemittanceFile(TimeStampedModel):
    SWITCH_CHOICES = [
        ('mediswitch', 'MediSwitch'),
        ('healthbridge', 'Healthbridge'),
        ('medikredit', 'MediKredit'),
        ('manual', 'Manual Upload'),
        ('other', 'Other')
    ]
    switch_provider = models.CharField(max_length=20, choices=SWITCH_CHOICES, default='manual')
    file_name = models.CharField(max_length=255)
    file = models.FileField(upload_to='remittance_files/%Y/%m/')
    received_date = models.DateField(auto_now_add=True)
    payment_date = models.DateField(null=True, blank=True)
    total_records = models.IntegerField(default=0)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    
    PROCESS_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('error', 'Error')
    ]
    processed_status = models.CharField(max_length=20, choices=PROCESS_STATUS_CHOICES, default='pending')
    raw_content = JSONField(default=dict, blank=True)
    error_log = models.TextField(blank=True)
    records_matched = models.IntegerField(default=0)
    records_unmatched = models.IntegerField(default=0)

    class Meta:
        ordering = ['-received_date']
        verbose_name = 'Remittance File'
        verbose_name_plural = 'Remittance Files'

    def __str__(self):
        return f"{self.file_name} ({self.received_date})"

class RemittanceLine(models.Model):
    remittance_file = models.ForeignKey(RemittanceFile, on_delete=models.CASCADE, related_name='lines')
    practice_number = models.CharField(max_length=20)
    scheme_name = models.CharField(max_length=255, blank=True)
    membership_number = models.CharField(max_length=50)
    dependent_code = models.CharField(max_length=5, blank=True)
    patient_name = models.CharField(max_length=255, blank=True)
    date_of_service = models.DateField()
    tariff_code = models.CharField(max_length=20)
    amount_claimed = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_approved = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reason_code = models.CharField(max_length=20, blank=True)
    reason_description = models.CharField(max_length=500, blank=True)
    
    MATCH_STATUS_CHOICES = [
        ('unmatched', 'Unmatched'),
        ('auto_matched', 'Auto Matched'),
        ('manual_matched', 'Manually Matched'),
        ('no_match', 'No Match Found')
    ]
    match_status = models.CharField(max_length=20, choices=MATCH_STATUS_CHOICES, default='unmatched')
    matched_claim_line_item = models.ForeignKey('claims.ClaimLineItem', on_delete=models.SET_NULL, null=True, blank=True, related_name='remittance_matches')

    class Meta:
        ordering = ['id']
        verbose_name = 'Remittance Line'
        verbose_name_plural = 'Remittance Lines'

    def __str__(self):
        return f"{self.practice_number} - {self.membership_number} - {self.tariff_code} ({self.date_of_service})"

class ReconciliationLog(TimeStampedModel):
    remittance_line = models.ForeignKey(RemittanceLine, on_delete=models.CASCADE, related_name='match_logs')
    claim_line_item = models.ForeignKey('claims.ClaimLineItem', on_delete=models.SET_NULL, null=True, blank=True)
    
    MATCH_METHOD_CHOICES = [
        ('auto_exact', 'Automatic Exact Match'),
        ('auto_fuzzy', 'Automatic Fuzzy Match'),
        ('manual', 'Manual Match')
    ]
    match_method = models.CharField(max_length=20, choices=MATCH_METHOD_CHOICES)
    match_confidence = models.IntegerField(default=0, help_text='0-100')
    matched_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Reconciliation Log'
        verbose_name_plural = 'Reconciliation Logs'

    def __str__(self):
        return f"Log for {self.remittance_line}"
"""

files["parsers/base.py"] = """import abc
from datetime import datetime
from decimal import Decimal

class BaseRemittanceParser(abc.ABC):
    def __init__(self, file_content: str):
        self.file_content = file_content

    @abc.abstractmethod
    def parse(self) -> list[dict]:
        pass

    def validate_row(self, row: dict) -> dict:
        # Convert amounts to Decimal
        for field in ['amount_claimed', 'amount_approved', 'amount_paid']:
            if field in row:
                try:
                    row[field] = Decimal(str(row[field]))
                except (ValueError, TypeError, decimal.InvalidOperation):
                    row[field] = Decimal('0.00')

        # Parse date if it's a string
        if 'date_of_service' in row and isinstance(row['date_of_service'], str):
            try:
                # Attempt common formats
                for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y%m%d'):
                    try:
                        row['date_of_service'] = datetime.strptime(row['date_of_service'], fmt).date()
                        break
                    except ValueError:
                        pass
            except Exception:
                pass
        return row
"""

files["parsers/csv_parser.py"] = """import csv
import io
from .base import BaseRemittanceParser

class CSVRemittanceParser(BaseRemittanceParser):
    COLUMN_MAP = {
        'practice no': 'practice_number',
        'practicenumber': 'practice_number',
        'practice_number': 'practice_number',
        'scheme': 'scheme_name',
        'scheme_name': 'scheme_name',
        'member no': 'membership_number',
        'membership_number': 'membership_number',
        'member number': 'membership_number',
        'dep': 'dependent_code',
        'dependent': 'dependent_code',
        'dependent_code': 'dependent_code',
        'patient': 'patient_name',
        'patient_name': 'patient_name',
        'date': 'date_of_service',
        'date_of_service': 'date_of_service',
        'tariff': 'tariff_code',
        'tariff_code': 'tariff_code',
        'claimed': 'amount_claimed',
        'amount_claimed': 'amount_claimed',
        'approved': 'amount_approved',
        'amount_approved': 'amount_approved',
        'paid': 'amount_paid',
        'amount_paid': 'amount_paid',
        'reason': 'reason_code',
        'reason_code': 'reason_code',
        'description': 'reason_description',
        'reason_description': 'reason_description'
    }

    def parse(self) -> list[dict]:
        reader = csv.DictReader(io.StringIO(self.file_content))
        results = []
        for row in reader:
            normalized_row = {}
            for k, v in row.items():
                if not k: continue
                norm_k = k.lower().strip()
                if norm_k in self.COLUMN_MAP:
                    normalized_row[self.COLUMN_MAP[norm_k]] = v
            results.append(self.validate_row(normalized_row))
        return results
"""

files["parsers/xml_parser.py"] = """import xml.etree.ElementTree as ET
from .base import BaseRemittanceParser

class XMLRemittanceParser(BaseRemittanceParser):
    def parse(self) -> list[dict]:
        root = ET.fromstring(self.file_content)
        results = []
        # Expecting remittance lines to be direct children or under a specific tag
        for child in root:
            row = {}
            for elem in child:
                tag = elem.tag.lower().replace('-', '_')
                row[tag] = elem.text
            
            # Additional logic to map to standard keys could be added here
            if row:
                results.append(self.validate_row(row))
        return results
"""

files["parsers/pipe_parser.py"] = """from .base import BaseRemittanceParser
from decimal import Decimal

class PipeDelimitedParser(BaseRemittanceParser):
    def parse(self) -> list[dict]:
        lines = self.file_content.splitlines()
        results = []
        
        current_provider = None
        current_scheme = None
        current_member = None
        current_patient = None
        current_treatment = None
        
        for line in lines:
            if not line.strip():
                continue
            parts = line.split('|')
            record_type = parts[0]
            
            if record_type == 'S':
                current_provider = parts[1] if len(parts) > 1 else ''
            elif record_type == 'M':
                current_scheme = parts[1] if len(parts) > 1 else ''
                current_member = parts[2] if len(parts) > 2 else ''
            elif record_type == 'P':
                current_patient = parts[2] if len(parts) > 2 else ''
                # dependent code usually around parts[3] or similar, keeping generic
            elif record_type == 'T':
                current_treatment = {
                    'practice_number': current_provider,
                    'scheme_name': current_scheme,
                    'membership_number': current_member,
                    'patient_name': current_patient,
                    'date_of_service': parts[1] if len(parts) > 1 else None,
                    'tariff_code': parts[2] if len(parts) > 2 else None,
                    'amount_claimed': Decimal(parts[3]) / 100 if len(parts) > 3 and parts[3] else Decimal(0)
                }
            elif record_type == 'Z':
                if current_treatment:
                    current_treatment['amount_approved'] = Decimal(parts[1]) / 100 if len(parts) > 1 and parts[1] else Decimal(0)
                    current_treatment['amount_paid'] = Decimal(parts[2]) / 100 if len(parts) > 2 and parts[2] else Decimal(0)
                    results.append(self.validate_row(current_treatment))
                    # Note: we might need to link R records if they follow
            elif record_type == 'R':
                if results:
                    last_record = results[-1]
                    last_record['reason_code'] = parts[1] if len(parts) > 1 else ''
                    last_record['reason_description'] = parts[2] if len(parts) > 2 else ''
        return results
"""

files["matching.py"] = """from datetime import timedelta
from .models import ReconciliationLog
from django.db.models import Q
from claims.models import ClaimLineItem

class AutoMatcher:
    def __init__(self):
        pass

    def match_remittance_file(self, remittance_file):
        summary = {'matched': 0, 'unmatched': 0, 'errors': 0}
        affected_claims = set()

        for line in remittance_file.lines.all():
            matches = ClaimLineItem.objects.filter(
                claim__practice__bhf_practice_number=line.practice_number,
                claim__patient_scheme__membership_number=line.membership_number,
                claim__patient_scheme__dependent_code=line.dependent_code,
                claim__date_of_service=line.date_of_service,
                tariff_code=line.tariff_code
            )

            if matches.count() == 1:
                match = matches.first()
                line.match_status = 'auto_matched'
                line.matched_claim_line_item = match
                line.save()

                # Update ClaimLineItem
                match.amount_paid = line.amount_paid
                match.amount_patient_liable = match.amount_billed - match.amount_paid - match.amount_scheme_discount
                match.line_status = 'paid' if match.amount_paid >= match.amount_billed else 'partially_paid'
                match.save()

                ReconciliationLog.objects.create(
                    remittance_line=line,
                    claim_line_item=match,
                    match_method='auto_exact',
                    match_confidence=100
                )
                summary['matched'] += 1
                affected_claims.add(match.claim)

            elif matches.count() == 0:
                # Fuzzy match
                fuzzy_matches = ClaimLineItem.objects.filter(
                    claim__practice__bhf_practice_number=line.practice_number,
                    claim__patient_scheme__membership_number=line.membership_number,
                    claim__patient_scheme__dependent_code=line.dependent_code,
                    tariff_code=line.tariff_code,
                    claim__date_of_service__gte=line.date_of_service - timedelta(days=3),
                    claim__date_of_service__lte=line.date_of_service + timedelta(days=3)
                )
                if fuzzy_matches.count() == 1:
                    match = fuzzy_matches.first()
                    line.match_status = 'auto_matched'
                    line.matched_claim_line_item = match
                    line.save()
                    
                    match.amount_paid = line.amount_paid
                    match.amount_patient_liable = match.amount_billed - match.amount_paid - match.amount_scheme_discount
                    match.line_status = 'paid' if match.amount_paid >= match.amount_billed else 'partially_paid'
                    match.save()

                    ReconciliationLog.objects.create(
                        remittance_line=line,
                        claim_line_item=match,
                        match_method='auto_fuzzy',
                        match_confidence=80
                    )
                    summary['matched'] += 1
                    affected_claims.add(match.claim)
                else:
                    line.match_status = 'unmatched'
                    line.save()
                    summary['unmatched'] += 1
            else:
                line.match_status = 'unmatched'
                line.save()
                summary['unmatched'] += 1

        for claim in affected_claims:
            claim.recalculate_totals()

        remittance_file.records_matched = summary['matched']
        remittance_file.records_unmatched = summary['unmatched']
        remittance_file.processed_status = 'completed'
        remittance_file.save()

        return summary
"""

files["tasks.py"] = """from celery import shared_task
import traceback
from .models import RemittanceFile, RemittanceLine
from .parsers.csv_parser import CSVRemittanceParser
from .parsers.xml_parser import XMLRemittanceParser
from .parsers.pipe_parser import PipeDelimitedParser
from .matching import AutoMatcher

@shared_task
def process_remittance_file(remittance_file_id):
    remittance_file = RemittanceFile.objects.get(id=remittance_file_id)
    remittance_file.processed_status = 'processing'
    remittance_file.save()

    try:
        content = remittance_file.file.read().decode('utf-8')
        ext = remittance_file.file.name.lower().split('.')[-1]
        
        parser = None
        if ext == 'csv':
            parser = CSVRemittanceParser(content)
        elif ext == 'xml':
            parser = XMLRemittanceParser(content)
        elif ext in ['txt', 'era']:
            parser = PipeDelimitedParser(content)
        else:
            raise ValueError("Unsupported file format")

        parsed_data = parser.parse()
        remittance_file.raw_content = {'data': parsed_data}
        remittance_file.total_records = len(parsed_data)
        remittance_file.save()

        for row in parsed_data:
            RemittanceLine.objects.create(
                remittance_file=remittance_file,
                practice_number=row.get('practice_number', ''),
                scheme_name=row.get('scheme_name', ''),
                membership_number=row.get('membership_number', ''),
                dependent_code=row.get('dependent_code', ''),
                patient_name=row.get('patient_name', ''),
                date_of_service=row.get('date_of_service'),
                tariff_code=row.get('tariff_code', ''),
                amount_claimed=row.get('amount_claimed', 0),
                amount_approved=row.get('amount_approved', 0),
                amount_paid=row.get('amount_paid', 0),
                reason_code=row.get('reason_code', ''),
                reason_description=row.get('reason_description', '')
            )

        matcher = AutoMatcher()
        matcher.match_remittance_file(remittance_file)

    except Exception as e:
        remittance_file.processed_status = 'error'
        remittance_file.error_log = traceback.format_exc()
        remittance_file.save()
"""

files["forms.py"] = """from django import forms
from .models import RemittanceFile

class RemittanceFileUploadForm(forms.Form):
    file = forms.FileField()
    switch_provider = forms.ChoiceField(choices=RemittanceFile.SWITCH_CHOICES)
    payment_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

class ManualMatchForm(forms.Form):
    remittance_line_id = forms.IntegerField(widget=forms.HiddenInput)
    claim_line_item_id = forms.IntegerField()
    notes = forms.CharField(required=False, widget=forms.Textarea)
"""

files["views.py"] = """from django.shortcuts import render, redirect, get_object_or_404
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

def manual_match_view(request):
    if request.method == 'POST':
        form = ManualMatchForm(request.POST)
        if form.is_valid():
            remittance_line_id = form.cleaned_data['remittance_line_id']
            claim_line_item_id = form.cleaned_data['claim_line_item_id']
            notes = form.cleaned_data['notes']

            remittance_line = get_object_or_404(RemittanceLine, id=remittance_line_id)
            claim_line_item = get_object_or_404(ClaimLineItem, id=claim_line_item_id)

            remittance_line.matched_claim_line_item = claim_line_item
            remittance_line.match_status = 'manual_matched'
            remittance_line.save()

            claim_line_item.amount_paid = remittance_line.amount_paid
            claim_line_item.amount_patient_liable = claim_line_item.amount_billed - claim_line_item.amount_paid - claim_line_item.amount_scheme_discount
            claim_line_item.line_status = 'paid' if claim_line_item.amount_paid >= claim_line_item.amount_billed else 'partially_paid'
            claim_line_item.save()
            claim_line_item.claim.recalculate_totals()

            ReconciliationLog.objects.create(
                remittance_line=remittance_line,
                claim_line_item=claim_line_item,
                match_method='manual',
                matched_by=request.user,
                notes=notes
            )

            messages.success(request, 'Manually matched successfully.')
            return redirect(request.META.get('HTTP_REFERER', reverse('reconciliation:dashboard')))
    return redirect('reconciliation:dashboard')
"""

files["urls.py"] = """from django.urls import path
from . import views

app_name = 'reconciliation'

urlpatterns = [
    path('', views.ReconciliationDashboardView.as_view(), name='dashboard'),
    path('files/', views.RemittanceFileListView.as_view(), name='file_list'),
    path('files/upload/', views.RemittanceFileUploadView.as_view(), name='upload'),
    path('files/<int:pk>/', views.RemittanceFileDetailView.as_view(), name='file_detail'),
    path('unmatched/', views.UnmatchedLinesView.as_view(), name='unmatched'),
    path('match/', views.manual_match_view, name='manual_match'),
]
"""

files["admin.py"] = """from django.contrib import admin
from .models import RemittanceFile, RemittanceLine, ReconciliationLog

@admin.register(RemittanceFile)
class RemittanceFileAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'switch_provider', 'received_date', 'processed_status', 'total_records', 'records_matched', 'records_unmatched')
    list_filter = ('processed_status', 'switch_provider')
    search_fields = ('file_name',)

@admin.register(RemittanceLine)
class RemittanceLineAdmin(admin.ModelAdmin):
    list_display = ('practice_number', 'membership_number', 'date_of_service', 'tariff_code', 'amount_paid', 'match_status')
    list_filter = ('match_status',)
    search_fields = ('membership_number', 'practice_number', 'tariff_code')

admin.site.register(ReconciliationLog)
"""

files["templates/reconciliation/dashboard.html"] = """{% extends 'base.html' %}

{% block content %}
<div class="container mt-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h1>Reconciliation</h1>
        <a href="{% url 'reconciliation:upload' %}" class="btn btn-primary">Upload Remittance File</a>
    </div>

    <div class="row mb-4">
        <div class="col-md-3">
            <div class="card bg-light">
                <div class="card-body">
                    <h5 class="card-title">Total Files</h5>
                    <p class="card-text h3">{{ total_files }}</p>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card bg-success text-white">
                <div class="card-body">
                    <h5 class="card-title">Lines Matched</h5>
                    <p class="card-text h3">{{ total_matched }}</p>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card bg-warning">
                <div class="card-body">
                    <h5 class="card-title">Lines Unmatched</h5>
                    <p class="card-text h3">{{ total_unmatched }}</p>
                    <a href="{% url 'reconciliation:unmatched' %}" class="btn btn-sm btn-dark mt-2">View Unmatched <span class="badge bg-danger">{{ total_unmatched }}</span></a>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card bg-info text-white">
                <div class="card-body">
                    <h5 class="card-title">Match Rate</h5>
                    <p class="card-text h3">{{ match_rate|floatformat:1 }}%</p>
                </div>
            </div>
        </div>
    </div>

    <h3>Recent Files</h3>
    <table class="table table-striped">
        <thead>
            <tr>
                <th>File Name</th>
                <th>Switch</th>
                <th>Date</th>
                <th>Status</th>
                <th>Records</th>
                <th>Matched</th>
                <th>Unmatched</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for file in recent_files %}
            <tr>
                <td>{{ file.file_name }}</td>
                <td>{{ file.get_switch_provider_display }}</td>
                <td>{{ file.received_date }}</td>
                <td><span class="badge bg-secondary">{{ file.get_processed_status_display }}</span></td>
                <td>{{ file.total_records }}</td>
                <td>{{ file.records_matched }}</td>
                <td>{{ file.records_unmatched }}</td>
                <td>
                    <a href="{% url 'reconciliation:file_detail' file.pk %}" class="btn btn-sm btn-info">View</a>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
"""

files["templates/reconciliation/remittancefile_list.html"] = """{% extends 'base.html' %}

{% block content %}
<div class="container mt-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h1>Remittance Files</h1>
        <a href="{% url 'reconciliation:upload' %}" class="btn btn-primary">Upload Remittance File</a>
    </div>

    <table class="table table-striped">
        <thead>
            <tr>
                <th>File Name</th>
                <th>Switch</th>
                <th>Date</th>
                <th>Status</th>
                <th>Records</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for file in files %}
            <tr>
                <td>{{ file.file_name }}</td>
                <td>{{ file.get_switch_provider_display }}</td>
                <td>{{ file.received_date }}</td>
                <td>{{ file.get_processed_status_display }}</td>
                <td>{{ file.total_records }}</td>
                <td>
                    <a href="{% url 'reconciliation:file_detail' file.pk %}" class="btn btn-sm btn-info">View</a>
                </td>
            </tr>
            {% empty %}
            <tr><td colspan="6">No files found.</td></tr>
            {% endfor %}
        </tbody>
    </table>
    
    {% if is_paginated %}
    <div class="pagination">
        <span class="page-links">
            {% if page_obj.has_previous %}
                <a href="?page={{ page_obj.previous_page_number }}">previous</a>
            {% endif %}
            <span class="page-current">
                Page {{ page_obj.number }} of {{ page_obj.paginator.num_pages }}.
            </span>
            {% if page_obj.has_next %}
                <a href="?page={{ page_obj.next_page_number }}">next</a>
            {% endif %}
        </span>
    </div>
    {% endif %}
</div>
{% endblock %}
"""

files["templates/reconciliation/remittancefile_detail.html"] = """{% extends 'base.html' %}

{% block content %}
<div class="container mt-4">
    <h2>Remittance File: {{ file.file_name }}</h2>
    
    <div class="card mb-4">
        <div class="card-body">
            <p><strong>Switch:</strong> {{ file.get_switch_provider_display }}</p>
            <p><strong>Date:</strong> {{ file.received_date }}</p>
            <p><strong>Status:</strong> {{ file.get_processed_status_display }}</p>
            <p><strong>Total Records:</strong> {{ file.total_records }}</p>
            <p><strong>Matched:</strong> {{ file.records_matched }} | <strong>Unmatched:</strong> {{ file.records_unmatched }}</p>
            
            <div class="progress">
                {% if file.total_records > 0 %}
                <div class="progress-bar bg-success" role="progressbar" style="width: {% widthratio file.records_matched file.total_records 100 %}%">
                    {% widthratio file.records_matched file.total_records 100 %}%
                </div>
                {% endif %}
            </div>
        </div>
    </div>

    <h4>Lines</h4>
    <table class="table table-sm table-striped">
        <thead>
            <tr>
                <th>Practice No</th>
                <th>Scheme</th>
                <th>Member No</th>
                <th>Dep</th>
                <th>Patient</th>
                <th>Date</th>
                <th>Tariff</th>
                <th>Claimed</th>
                <th>Approved</th>
                <th>Paid</th>
                <th>Reason</th>
                <th>Status</th>
                <th>Matched To</th>
            </tr>
        </thead>
        <tbody>
            {% for line in lines %}
            <tr>
                <td>{{ line.practice_number }}</td>
                <td>{{ line.scheme_name }}</td>
                <td>{{ line.membership_number }}</td>
                <td>{{ line.dependent_code }}</td>
                <td>{{ line.patient_name }}</td>
                <td>{{ line.date_of_service|date:"Y-m-d" }}</td>
                <td>{{ line.tariff_code }}</td>
                <td>{{ line.amount_claimed }}</td>
                <td>{{ line.amount_approved }}</td>
                <td>{{ line.amount_paid }}</td>
                <td>{{ line.reason_code }}</td>
                <td>
                    <span class="badge {% if line.match_status == 'unmatched' %}bg-danger{% else %}bg-success{% endif %}">
                        {{ line.get_match_status_display }}
                    </span>
                </td>
                <td>
                    {% if line.matched_claim_line_item %}
                        Claim ID: {{ line.matched_claim_line_item.claim.id }}
                    {% else %}
                        <button class="btn btn-sm btn-outline-primary" data-bs-toggle="modal" data-bs-target="#matchModal{{ line.id }}">Match</button>
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
"""

files["templates/reconciliation/remittancefile_upload.html"] = """{% extends 'base.html' %}
{% load crispy_forms_tags %}

{% block content %}
<div class="container mt-4">
    <h2>Upload Remittance File</h2>
    <form method="post" enctype="multipart/form-data">
        {% csrf_token %}
        {{ form|crispy }}
        <button type="submit" class="btn btn-primary">Upload and Process</button>
        <a href="{% url 'reconciliation:file_list' %}" class="btn btn-secondary">Cancel</a>
    </form>
</div>
{% endblock %}
"""

files["templates/reconciliation/unmatched_list.html"] = """{% extends 'base.html' %}

{% block content %}
<div class="container mt-4">
    <h2>Unmatched Remittance Lines</h2>
    
    <form method="get" class="mb-4">
        <div class="row">
            <div class="col-md-4">
                <input type="text" name="q" class="form-control" placeholder="Search Member No" value="{{ request.GET.q }}">
            </div>
            <div class="col-md-4">
                <input type="text" name="practice" class="form-control" placeholder="Practice No" value="{{ request.GET.practice }}">
            </div>
            <div class="col-md-4">
                <button type="submit" class="btn btn-primary">Search</button>
            </div>
        </div>
    </form>

    <table class="table table-sm table-striped">
        <thead>
            <tr>
                <th>Practice No</th>
                <th>Member No</th>
                <th>Date</th>
                <th>Tariff</th>
                <th>Paid</th>
                <th>Action</th>
            </tr>
        </thead>
        <tbody>
            {% for line in lines %}
            <tr>
                <td>{{ line.practice_number }}</td>
                <td>{{ line.membership_number }}</td>
                <td>{{ line.date_of_service }}</td>
                <td>{{ line.tariff_code }}</td>
                <td>{{ line.amount_paid }}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" data-bs-toggle="modal" data-bs-target="#matchModal{{ line.id }}">Match</button>
                </td>
            </tr>
            {% empty %}
            <tr><td colspan="6">No unmatched lines found.</td></tr>
            {% endfor %}
        </tbody>
    </table>

    {% if is_paginated %}
    <div class="pagination">
        <span class="page-links">
            {% if page_obj.has_previous %}
                <a href="?page={{ page_obj.previous_page_number }}{% if request.GET.q %}&q={{ request.GET.q }}{% endif %}">previous</a>
            {% endif %}
            <span class="page-current">
                Page {{ page_obj.number }} of {{ page_obj.paginator.num_pages }}.
            </span>
            {% if page_obj.has_next %}
                <a href="?page={{ page_obj.next_page_number }}{% if request.GET.q %}&q={{ request.GET.q }}{% endif %}">next</a>
            {% endif %}
        </span>
    </div>
    {% endif %}
</div>
{% endblock %}
"""

for fname, content in files.items():
    with open(os.path.join(base_dir, fname), "w", encoding="utf-8") as f:
        f.write(content)
print("Done")
