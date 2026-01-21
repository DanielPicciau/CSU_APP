"""
URL configuration for CSU Tracker project.
"""

from django.contrib import admin
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import include, path
from django.views.generic import TemplateView

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


def service_worker_view(request):
    """Serve service worker with proper headers for root scope."""
    sw_content = render_to_string('pwa/sw.js')
    response = HttpResponse(sw_content, content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    return response


urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    
    # API Authentication (JWT)
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    
    # Apps
    path("accounts/", include("accounts.urls")),
    path("api/accounts/", include("accounts.api_urls")),
    path("tracking/", include("tracking.urls")),
    path("api/tracking/", include("tracking.api_urls")),
    path("notifications/", include("notifications.urls")),
    path("api/notifications/", include("notifications.api_urls")),
    
    # PWA
    path("manifest.json", TemplateView.as_view(
        template_name="pwa/manifest.json",
        content_type="application/json"
    ), name="manifest"),
    path("sw.js", service_worker_view, name="service_worker"),
    path("offline/", TemplateView.as_view(template_name="pwa/offline.html"), name="offline"),
    
    # Home
    path("", include("tracking.home_urls")),
]
