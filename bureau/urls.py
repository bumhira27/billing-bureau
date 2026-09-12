from django.urls import path
from . import views

app_name = 'bureau'

urlpatterns = [
    path('profile/', views.BureauProfileUpdateView.as_view(), name='profile_update'),
    path('invoices/', views.PracticeInvoiceListView.as_view(), name='invoice_list'),
]
