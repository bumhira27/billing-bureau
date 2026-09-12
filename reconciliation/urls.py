from django.urls import path
from . import views

app_name = 'reconciliation'

urlpatterns = [
    path('', views.ReconciliationDashboardView.as_view(), name='dashboard'),
    path('files/', views.RemittanceFileListView.as_view(), name='file_list'),
    path('files/upload/', views.RemittanceFileUploadView.as_view(), name='upload'),
    path('files/<int:pk>/', views.RemittanceFileDetailView.as_view(), name='file_detail'),
    path('unmatched/', views.UnmatchedLinesView.as_view(), name='unmatched'),
    path('match/', views.manual_match_view, name='manual_match'),
]
