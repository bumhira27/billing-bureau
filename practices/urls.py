from django.urls import path
from . import views

app_name = 'practices'

urlpatterns = [
    path('', views.PracticeListView.as_view(), name='list'),
    path('create/', views.PracticeCreateView.as_view(), name='create'),
    path('<int:pk>/', views.PracticeDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.PracticeUpdateView.as_view(), name='update'),
]
