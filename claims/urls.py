from django.urls import path
from . import views

app_name = 'claims'

urlpatterns = [
    path('', views.ClaimListView.as_view(), name='list'),
    path('create/', views.ClaimCreateView.as_view(), name='create'),
    path('<int:pk>/', views.ClaimDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.ClaimUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.ClaimDeleteView.as_view(), name='delete'),
    path('<int:pk>/submit/', views.claim_submit, name='submit'),
    path('<int:pk>/edi-submit/', views.claim_edi_submit, name='edi_submit'),
    path('<int:pk>/add_note/', views.claim_add_note, name='add_note'),
]
