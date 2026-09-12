from django.http import JsonResponse
from django.db.models import Q
from .models import ICD10Code, TariffCode, RejectionCode

def icd10_search(request):
    """
    Search ICD-10 codes for autocomplete.
    """
    q = request.GET.get('q', '')
    if q:
        results = ICD10Code.objects.filter(
            Q(code__icontains=q) | Q(description__icontains=q)
        ).filter(is_active=True)[:20]
    else:
        results = ICD10Code.objects.none()
    
    data = [{'id': obj.id, 'code': obj.code, 'description': obj.description} for obj in results]
    return JsonResponse(data, safe=False)

def tariff_search(request):
    """
    Search tariff codes for autocomplete.
    """
    q = request.GET.get('q', '')
    if q:
        results = TariffCode.objects.filter(
            Q(code__icontains=q) | Q(description__icontains=q)
        ).filter(is_active=True)[:20]
    else:
        results = TariffCode.objects.none()
        
    data = [{
        'id': obj.id, 
        'code': obj.code, 
        'description': obj.description,
        'default_amount': str(obj.default_amount) if obj.default_amount else None
    } for obj in results]
    return JsonResponse(data, safe=False)

def rejection_search(request):
    """
    Search rejection codes for autocomplete.
    """
    q = request.GET.get('q', '')
    if q:
        results = RejectionCode.objects.filter(
            Q(code__icontains=q) | Q(description__icontains=q)
        ).filter(is_active=True)[:20]
    else:
        results = RejectionCode.objects.none()
        
    data = [{'id': obj.id, 'code': obj.code, 'description': obj.description} for obj in results]
    return JsonResponse(data, safe=False)


from django.views.generic import ListView

class RejectionCodeListView(ListView):
    model = RejectionCode
    template_name = 'reference_data/rejection_code_list.html'
    context_object_name = 'codes'
    paginate_by = 50

    def get_queryset(self):
        qs = RejectionCode.objects.filter(is_active=True)
        q = self.request.GET.get('q', '').strip()
        cat = self.request.GET.get('category', '').strip()
        if q:
            qs = qs.filter(Q(code__icontains=q) | Q(description__icontains=q) | Q(suggested_action__icontains=q))
        if cat:
            qs = qs.filter(category=cat)
        return qs.order_by('code')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = RejectionCode.CATEGORY_CHOICES
        context['current_category'] = self.request.GET.get('category', '')
        context['current_q'] = self.request.GET.get('q', '')
        return context

