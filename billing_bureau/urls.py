from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('practices/', include('practices.urls')),
    path('patients/', include('patients.urls')),
    path('claims/', include('claims.urls')),
    path('reconciliation/', include('reconciliation.urls')),
    path('collections/', include('billing_collections.urls')),
    path('reference/', include('reference_data.urls')),
    path('bureau/', include('bureau.urls')),
    path('api/v1/', include('api.v1_urls')),
    path('accounts/', include('django.contrib.auth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
