from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('practices/', include('practices.urls')),
    path('patients/', include('patients.urls')),
    path('claims/', include('claims.urls')),
    path('reconciliation/', include('reconciliation.urls')),
    path('collections/', include('billing_collections.urls')),
    path('reference/', include('reference_data.urls')),
]

if getattr(settings, 'MFA_ENABLED', False):
    from two_factor.urls import urlpatterns as tf_urls
    urlpatterns += [
        path('', include(tf_urls)),
    ]
else:
    urlpatterns += [
        path('account/login/', auth_views.LoginView.as_view(template_name='registration/login.html', redirect_authenticated_user=True), name='login'),
        path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html', redirect_authenticated_user=True)),
        path('login/', auth_views.LoginView.as_view(template_name='registration/login.html', redirect_authenticated_user=True)),
        path('account/logout/', auth_views.LogoutView.as_view(next_page='/account/login/'), name='logout'),
        path('accounts/logout/', auth_views.LogoutView.as_view(next_page='/account/login/')),
        path('logout/', auth_views.LogoutView.as_view(next_page='/account/login/')),
    ]

urlpatterns += [
    path('accounts/', include('django.contrib.auth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
