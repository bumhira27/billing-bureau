from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, F
from django.utils import timezone
from claims.models import Claim
from billing_collections.models import Payment
from reconciliation.models import RemittanceLine

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        user = self.request.user
        
        is_admin = user.is_superuser or user.groups.filter(name='BureauAdmin').exists()
        
        base_claims = Claim.objects.all() if is_admin else Claim.objects.filter(practice__users=user)
        base_payments = Payment.objects.all() if is_admin else Payment.objects.filter(claim__practice__users=user)
        
        # Needs Attention
        context['claims_rejected_count'] = base_claims.filter(claim_status='rejected').count()
        
        if is_admin:
            context['unmatched_payments_count'] = RemittanceLine.objects.filter(is_matched=False).count()
        else:
            context['unmatched_payments_count'] = 0
            
        context['outstanding_statements_count'] = base_claims.filter(
            total_paid__lt=F('total_billed'), 
            claim_status__in=['submitted', 'partially_paid']
        ).count()
        
        # This Month Metrics
        this_month_claims = base_claims.filter(date_of_service__year=now.year, date_of_service__month=now.month)
        billed = this_month_claims.aggregate(Sum('total_billed'))['total_billed__sum'] or 0.0
        
        this_month_payments = base_payments.filter(payment_date__year=now.year, payment_date__month=now.month)
        collected = this_month_payments.aggregate(Sum('amount'))['amount__sum'] or 0.0
        
        context['billed_this_month'] = round(float(billed), 2)
        context['collected_this_month'] = round(float(collected), 2)
        
        # Outstanding is total lifetime outstanding
        outstanding_qs = base_claims.filter(total_paid__lt=F('total_billed')).annotate(outstanding=F('total_billed') - F('total_paid'))
        context['total_outstanding'] = round(float(outstanding_qs.aggregate(total=Sum('outstanding'))['total'] or 0), 2)
        
        # Lists
        context['recent_claims'] = base_claims.order_by('-created_at')[:10]
        context['recent_payments'] = base_payments.order_by('-created_at')[:10]
        
        return context
