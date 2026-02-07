"""
URL configuration for CSU Tracker project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.core.cache import cache
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import include, path
from django.views.decorators.cache import cache_control
from django.views.generic import TemplateView

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


# ---------------------------------------------------------------------------
# PWA views — rendered once, then served from cache for 15 minutes.
# These MUST NOT hit the database or session on every request.
# ---------------------------------------------------------------------------
@cache_control(public=True, max_age=900)
def service_worker_view(request):
    """Serve service worker with proper headers for root scope."""
    cache_key = "pwa:sw.js"
    content = cache.get(cache_key)
    if content is None:
        content = render_to_string('pwa/sw.js')
        cache.set(cache_key, content, 900)  # 15 min
    response = HttpResponse(content, content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    return response


@cache_control(public=True, max_age=900)
def manifest_view(request):
    """Serve manifest.json with caching — no DB, no session."""
    cache_key = "pwa:manifest.json"
    content = cache.get(cache_key)
    if content is None:
        content = render_to_string('pwa/manifest.json')
        cache.set(cache_key, content, 900)  # 15 min
    return HttpResponse(content, content_type='application/json')


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
    path("subscriptions/", include("subscriptions.urls")),
    
    # PWA
    path("manifest.json", manifest_view, name="manifest"),
    path("sw.js", service_worker_view, name="service_worker"),
    path("offline/", TemplateView.as_view(template_name="pwa/offline.html"), name="offline"),
    
    # Home
    path("", include("tracking.home_urls")),
    
    # Legal
    path("legal/privacy-policy/", TemplateView.as_view(template_name="legal/privacy_policy.html"), name="privacy_policy"),
    path("legal/terms-of-service/", TemplateView.as_view(template_name="legal/terms_of_service.html"), name="terms_of_service"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
