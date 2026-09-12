from django.urls import path
from . import views

app_name = 'claims'

urlpatterns = [
    path('', views.ClaimListView.as_view(), name='list'),
    path('create/', views.ClaimCreateView.as_view(), name='create'),
    path('<int:pk>/', views.ClaimDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.ClaimUpdateView.as_view(), name='update'),
    path('<int:pk>/submit/', views.claim_submit, name='submit'),
    path('<int:pk>/edi-submit/', views.claim_edi_submit, name='edi_submit'),
    path('<int:pk>/rpa_submit/', views.claim_rpa_submit, name='rpa_submit'),
    path('<int:pk>/assign/', views.claim_assign, name='assign'),
    path('<int:pk>/add_note/', views.claim_add_note, name='add_note'),
    path('edi-logs/', views.EdiLogListView.as_view(), name='edi_logs'),
    path('rpa-logs/', views.RpaLogListView.as_view(), name='rpa_logs'),
    path('batch/', views.BatchCaptureView.as_view(), name='batch_capture'),
    path('upload-note/', views.UploadNoteView.as_view(), name='upload_note'),
    path('review-extracted/<int:pk>/', views.ReviewExtractedClaimView.as_view(), name='review_extracted'),
]
