from django.urls import reverse_lazy
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
        bureau_fee = round(total_paid * float(self.object.fee_percentage) / 100.0, 2)

        context['total_claims_count'] = claims.count()
        context['total_billed'] = total_billed
        context['total_collected'] = total_paid
        context['outstanding_balance'] = outstanding
        context['collection_rate'] = collection_rate
        context['bureau_fee_earned'] = bureau_fee

        context['recent_claims'] = claims.order_by('-date_of_service', '-created_at')[:10]
        context['patients'] = self.object.patients.all().prefetch_related('schemes')
        context['portal_credentials'] = self.object.portal_credentials.all()
        from credentials.models import MedicalAidPortalCredential
        context['bureau_credentials'] = MedicalAidPortalCredential.objects.all()
        from .forms import PortalCredentialForm
        context['credential_form'] = PortalCredentialForm()
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


from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import PortalCredential
from .forms import PortalCredentialForm


@require_POST
@login_required
def portal_credential_create(request, practice_pk):
    practice = get_object_or_404(Practice, pk=practice_pk)
    form = PortalCredentialForm(request.POST)
    if form.is_valid():
        cred = form.save(commit=False)
        cred.practice = practice
        cred.created_by = request.user
        cred.save()
        messages.success(request, f"Portal credentials for {cred.get_administrator_display()} configured.")
    else:
        messages.error(request, "Failed to save portal credentials. Please check inputs.")
    return redirect('practices:detail', pk=practice_pk)


@require_POST
@login_required
def portal_credential_test(request, pk):
    cred = get_object_or_404(PortalCredential, pk=pk)
    from django.utils import timezone
    from claims.rpa.discovery_bot import DiscoveryPortalBot
    from claims.rpa.medscheme_bot import MedschemePortalBot
    from claims.rpa.simulator_bot import SimulatorPortalBot

    if cred.administrator == 'discovery':
        bot = DiscoveryPortalBot(username=cred.username, password=cred.password, portal_url=cred.portal_url)
    elif cred.administrator == 'medscheme':
        bot = MedschemePortalBot(username=cred.username, password=cred.password, portal_url=cred.portal_url)
    else:
        bot = SimulatorPortalBot(username=cred.username, password=cred.password, portal_url=cred.portal_url)

    ok = bot.verify_login()
    if ok:
        cred.last_tested = timezone.now()
        cred.save(update_fields=['last_tested'])
        messages.success(request, f"Authentication verified for {cred.get_administrator_display()} ({cred.username}).")
    else:
        messages.error(request, f"Authentication test failed for {cred.get_administrator_display()}.")
    return redirect('practices:detail', pk=cred.practice_id)


@require_POST
@login_required
def portal_credential_delete(request, pk):
    cred = get_object_or_404(PortalCredential, pk=pk)
    practice_id = cred.practice_id
    admin_name = cred.get_administrator_display()
    cred.delete()
    messages.success(request, f"Removed {admin_name} portal credentials.")
    return redirect('practices:detail', pk=practice_id)
