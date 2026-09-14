from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from .models import Practice
from .forms import PracticeForm

from core.mixins import RBACQuerySetMixin

class CreatedByMixin:
    def form_valid(self, form):
        if hasattr(form.instance, 'created_by_id') and not form.instance.created_by_id:
            form.instance.created_by = self.request.user
        return super().form_valid(form)

class PracticeListView(LoginRequiredMixin, RBACQuerySetMixin, ListView):
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

class PracticeDetailView(LoginRequiredMixin, RBACQuerySetMixin, DetailView):
    model = Practice
    template_name = 'practices/practice_detail.html'
    context_object_name = 'practice'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.db.models import Sum
        from decimal import Decimal

        claims = self.object.claims.all()
        totals = claims.aggregate(
            total_billed=Sum('total_billed'),
            total_paid=Sum('total_paid')
        )
        total_billed = round(float(totals['total_billed'] or 0), 2)
        total_paid = round(float(totals['total_paid'] or 0), 2)
        outstanding = round(total_billed - total_paid, 2)
        collection_rate = round((total_paid / total_billed * 100), 1) if total_billed > 0 else 0.0

        context['total_claims_count'] = claims.count()
        context['total_billed'] = total_billed
        context['total_collected'] = total_paid
        context['outstanding_balance'] = outstanding
        context['collection_rate'] = collection_rate

        context['recent_claims'] = claims.order_by('-date_of_service', '-created_at')[:10]
        context['patients'] = self.object.patients.all().prefetch_related('schemes')
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

