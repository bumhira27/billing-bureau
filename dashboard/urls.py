from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='index'),
    path('practice/<int:pk>/', views.PracticeReportView.as_view(), name='practice_report'),
    path('export/', views.export_report, name='export'),
]
