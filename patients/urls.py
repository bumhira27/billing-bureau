from django.urls import path
from . import views

app_name = 'patients'

urlpatterns = [
    path('', views.PatientListView.as_view(), name='list'),
    path('create/<int:practice_id>/', views.PatientCreateView.as_view(), name='create'),
    path('<int:pk>/', views.PatientDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.PatientUpdateView.as_view(), name='update'),
    path('<int:patient_id>/scheme/add/', views.PatientSchemeCreateView.as_view(), name='add_scheme'),
    path('search/', views.patient_search_api, name='search_api'),
]
