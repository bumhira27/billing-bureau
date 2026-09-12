import datetime
from dateutil.relativedelta import relativedelta
from django.shortcuts import render
from django.views.generic import TemplateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count, F, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.http import HttpResponse

import openpyxl

from practices.models import Practice
from claims.models import Claim, ClaimLineItem
from billing_collections.models import Payment

class DashboardMixin:
    def get_dashboard_metrics(self, base_claims, now):
        claims_this_month = base_claims.filter(date_of_service__month=now.month, date_of_service__year=now.year)
        total_claims_this_month = claims_this_month.count()
        
        billed = round(float(claims_this_month.aggregate(total=Sum('total_billed'))['total'] or 0), 2)
        collected = round(float(claims_this_month.aggregate(total=Sum('total_paid'))['total'] or 0), 2)
        
        collection_rate = (collected / billed * 100) if billed > 0 else 0
        
        outstanding_qs = base_claims.filter(total_paid__lt=F('total_billed')).annotate(outstanding=F('total_billed') - F('total_paid'))
        total_outstanding = round(float(outstanding_qs.aggregate(total=Sum('outstanding'))['total'] or 0), 2)
        
        rejected = claims_this_month.filter(claim_status='rejected').count()
        rejection_rate = (rejected / total_claims_this_month * 100) if total_claims_this_month > 0 else 0
        
        # Claims by status
        status_counts = claims_this_month.values('claim_status').annotate(count=Count('id'))
        claims_by_status = {item['claim_status']: item['count'] for item in status_counts}
        
        # Monthly collections (last 6 months)
        six_months_ago = now.date() - relativedelta(months=5)
        six_months_ago = six_months_ago.replace(day=1)
        
        monthly_data = base_claims.filter(date_of_service__gte=six_months_ago).annotate(
            month=TruncMonth('date_of_service')
        ).values('month').annotate(
            billed=Sum('total_billed'),
            collected=Sum('total_paid')
        ).order_by('month')
        
        monthly_collections = []
        for item in monthly_data:
            if item['month']:
                monthly_collections.append({
                    'month': item['month'].strftime('%Y-%m'),
                    'billed': str(round(float(item['billed'] or 0), 2)),
                    'collected': str(round(float(item['collected'] or 0), 2))
                })
        
        # Ageing analysis
        today = now.date()
        thirty_days = today - datetime.timedelta(days=30)
        sixty_days = today - datetime.timedelta(days=60)
        ninety_days = today - datetime.timedelta(days=90)
        
        ageing_buckets = {'0-30': 0, '31-60': 0, '61-90': 0, '90+': 0}
        
        for claim in outstanding_qs:
            if not claim.date_of_service:
                continue
            if claim.date_of_service >= thirty_days:
                ageing_buckets['0-30'] += claim.outstanding
            elif claim.date_of_service >= sixty_days:
                ageing_buckets['31-60'] += claim.outstanding
            elif claim.date_of_service >= ninety_days:
                ageing_buckets['61-90'] += claim.outstanding
            else:
                ageing_buckets['90+'] += claim.outstanding
                
        # Convert Decimals to string/float for JSON serialization if needed
        for k, v in ageing_buckets.items():
            ageing_buckets[k] = float(v)

        return {
            'total_claims_this_month': total_claims_this_month,
            'total_billed_this_month': billed,
            'total_collected_this_month': collected,
            'collection_rate': round(collection_rate, 2),
            'total_outstanding': total_outstanding,
            'rejection_rate': round(rejection_rate, 2),
            'claims_by_status': claims_by_status,
            'monthly_collections': monthly_collections,
            'ageing_buckets': ageing_buckets,
        }

class DashboardView(LoginRequiredMixin, DashboardMixin, TemplateView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        
        total_practices = Practice.objects.filter(is_active=True).count()
        context['total_practices'] = total_practices
        
        base_claims = Claim.objects.all()
        metrics = self.get_dashboard_metrics(base_claims, now)
        context.update(metrics)
        
        context['recent_claims'] = Claim.objects.order_by('-created_at')[:10]
        context['recent_payments'] = Payment.objects.order_by('-created_at')[:10]
        
        # Top rejection codes
        top_codes = ClaimLineItem.objects.filter(rejection_code__isnull=False).exclude(rejection_code='').values(
            'rejection_code'
        ).annotate(count=Count('id')).order_by('-count')[:5]
        
        context['top_rejection_codes'] = top_codes
        
        return context

class PracticeReportView(LoginRequiredMixin, DashboardMixin, DetailView):
    model = Practice
    template_name = 'dashboard/practice_report.html'
    context_object_name = 'practice'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        
        base_claims = Claim.objects.filter(practice=self.object)
        metrics = self.get_dashboard_metrics(base_claims, now)
        context.update(metrics)
        
        context['recent_claims'] = base_claims.order_by('-created_at')[:10]
        context['recent_payments'] = Payment.objects.filter(claim__practice=self.object).order_by('-created_at')[:10]
        
        top_codes = ClaimLineItem.objects.filter(claim__practice=self.object, rejection_code__isnull=False).exclude(
            rejection_code=''
        ).values('rejection_code').annotate(count=Count('id')).order_by('-count')[:5]
        
        context['top_rejection_codes'] = top_codes
        
        return context

def export_report(request):
    practice_id = request.GET.get('practice_id')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    wb = openpyxl.Workbook()
    
    # Claims Summary
    ws1 = wb.active
    ws1.title = "Claims Summary"
    ws1.append(["Claim ID", "Practice", "Patient", "Date of Service", "Total Billed", "Total Paid", "Status"])
    
    claims = Claim.objects.all()
    if practice_id:
        claims = claims.filter(practice_id=practice_id)
    if date_from:
        claims = claims.filter(date_of_service__gte=date_from)
    if date_to:
        claims = claims.filter(date_of_service__lte=date_to)
        
    for c in claims:
        ws1.append([c.id, str(c.practice), str(c.patient), c.date_of_service, c.total_billed, c.total_paid, c.claim_status])
        
    # Payments
    ws2 = wb.create_sheet(title="Payments")
    ws2.append(["Payment Date", "Claim ID", "Patient", "Amount", "Source", "Reference"])
    
    payments = Payment.objects.all()
    if practice_id:
        payments = payments.filter(claim__practice_id=practice_id)
    if date_from:
        payments = payments.filter(payment_date__gte=date_from)
    if date_to:
        payments = payments.filter(payment_date__lte=date_to)
        
    for p in payments:
        ws2.append([p.payment_date, p.claim.id, str(p.claim.patient), p.amount, p.get_payment_source_display(), p.reference_number])
        
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=billing_report.xlsx'
    wb.save(response)
    
    return response
