from django.urls import path
from . import views

app_name = 'reference_data'

urlpatterns = [
    path('icd10/search/', views.icd10_search, name='reference_icd10_search'),
    path('tariff/search/', views.tariff_search, name='reference_tariff_search'),
    path('rejection/search/', views.rejection_search, name='reference_rejection_search'),
    path('rejections/', views.RejectionCodeListView.as_view(), name='rejection_list'),
]
