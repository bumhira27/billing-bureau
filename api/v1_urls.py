from django.urls import path
from . import views

app_name = 'api_v1'

urlpatterns = [
    path('claims/', views.claim_create_api, name='claim_create'),
    path('claims/<int:pk>/', views.claim_detail_api, name='claim_detail'),
    path('mobile/sync/', views.mobile_batch_sync_api, name='mobile_sync'),
]
