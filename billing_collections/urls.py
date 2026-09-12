from django.urls import path
from . import views

app_name = 'billing_collections'

urlpatterns = [
    path('', views.CollectionsOverviewView.as_view(), name='overview'),
    path('statements/', views.StatementListView.as_view(), name='statement_list'),
    path('statements/generate/', views.generate_statements_view, name='generate_statements'),
    path('statements/<int:pk>/', views.StatementDetailView.as_view(), name='statement_detail'),
    path('payments/', views.PaymentListView.as_view(), name='payment_list'),
    path('payments/create/', views.PaymentCreateView.as_view(), name='payment_create'),
    path('api/patient-balance/', views.patient_balance_api, name='patient_balance_api'),
    path('financials/', views.FinancialDashboardView.as_view(), name='financials'),
]
