"""
Security middleware for medical-grade application.
"""

import logging
import time
from typing import Callable

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin

from .security import (
    SECURITY_HEADERS,
    get_client_ip,
    audit_logger,
    is_suspicious_bot,
)

logger = logging.getLogger('security')


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add security headers to all responses."""
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        # Add security headers
        for header, value in SECURITY_HEADERS.items():
            if header not in response:
                response[header] = value
        
        # Add HSTS header in production
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        return response


class RateLimitMiddleware(MiddlewareMixin):
    """
    Global rate limiting middleware.
    
    Different limits for different endpoints:
    - Login: 5 attempts per minute
    - API: 100 requests per minute
    - General: 200 requests per minute
    """
    
    # Rate limit configurations (max_requests, window_seconds)
    LIMITS = {
        '/accounts/login/': (5, 60),
        '/accounts/password-reset/': (5, 900),
        '/accounts/password-reset/confirm/': (10, 900),
        '/accounts/mfa/verify/': (10, 600),
        '/accounts/mfa/': (10, 600),
        '/accounts/onboarding/account/': (3, 60),
        '/accounts/register/': (3, 60),
        '/admin/login/': (5, 60),
        '/api/accounts/register/': (3, 60),
        '/api/accounts/password/change/': (10, 600),
        '/api/token/': (10, 60),
        '/api/token/refresh/': (10, 60),
        '/api/': (100, 60),
        'default': (200, 60),
    }

    SENSITIVE_PATHS = [
        '/accounts/login/',
        '/accounts/password-reset/',
        '/accounts/password-reset/confirm/',
        '/accounts/mfa/',
        '/accounts/mfa/verify/',
        '/accounts/onboarding/account/',
        '/accounts/register/',
        '/admin/login/',
        '/api/accounts/register/',
        '/api/accounts/password/change/',
        '/api/token/',
        '/api/token/refresh/',
    ]
    
    # Paths to exclude from rate limiting
    EXCLUDED_PATHS = [
        '/static/',
        '/favicon.ico',
        '/manifest.json',
        '/sw.js',
    ]

    NORMALIZED_PATH_PREFIXES = {
        '/accounts/password-reset/confirm/': '/accounts/password-reset/confirm/',
    }

    @classmethod
    def normalize_rate_limit_path(cls, path: str) -> str:
        for prefix, normalized in cls.NORMALIZED_PATH_PREFIXES.items():
            if path.startswith(prefix):
                return normalized
        return path
    
    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        # Skip rate limiting in tests
        if getattr(settings, 'TESTING', False):
            return None
        
        # Skip excluded paths
        for excluded in self.EXCLUDED_PATHS:
            if request.path.startswith(excluded):
                return None
        
        # Skip rate limiting for cron endpoints with valid Authorization header
        # SECURITY: Query string tokens are no longer accepted
        if request.path.startswith('/notifications/cron/'):
            auth_header = request.headers.get('Authorization', '')
            cron_token_header = request.headers.get('X-Cron-Token', '')
            cron_secret = getattr(settings, 'CRON_WEBHOOK_SECRET', '')
            if cron_secret:
                import secrets as sec
                if auth_header.startswith('Bearer '):
                    if sec.compare_digest(auth_header[7:], cron_secret):
                        return None
                elif cron_token_header and sec.compare_digest(cron_token_header, cron_secret):
                    return None
        
        # Determine rate limit for this path
        max_requests, window = self.LIMITS['default']
        for path_prefix, limits in self.LIMITS.items():
            if path_prefix != 'default' and request.path.startswith(path_prefix):
                max_requests, window = limits
                break

        # Basic bot heuristics for sensitive endpoints
        if any(request.path.startswith(path) for path in self.SENSITIVE_PATHS):
            if not settings.DEBUG and is_suspicious_bot(request):
                # Stricter limit for suspicious clients
                max_requests, window = (2, 60)
        
        # Create cache key
        ip = get_client_ip(request)
        user_id = request.user.id if hasattr(request, 'user') and request.user.is_authenticated else 'anon'
        rate_limit_path = self.normalize_rate_limit_path(request.path)
        cache_key = f"ratelimit:global:{rate_limit_path}:{ip}:{user_id}"
        
        # Check rate limit - gracefully handle cache failures
        try:
            current = cache.get(cache_key, 0)
        except Exception as e:
            # Cache unavailable - allow request to proceed (fail open for availability)
            logger.warning(f"Cache unavailable for rate limiting: {e}")
            return None
        
        if current >= max_requests:
            logger.warning(
                f"Rate limit exceeded: {rate_limit_path}",
                extra={
                    'ip': ip,
                    'path': rate_limit_path,
                    'limit': max_requests,
                }
            )
            audit_logger.log_security_event(
                'RATE_LIMIT_EXCEEDED',
                request,
                {'path': rate_limit_path, 'limit': max_requests}
            )
            return JsonResponse(
                {
                    'error': 'Rate limit exceeded. Please try again later.',
                    'retry_after': window,
                },
                status=429,
                headers={'Retry-After': str(window)}
            )
        
        # Increment counter - ignore cache failures
        try:
            cache.set(cache_key, current + 1, window)
        except Exception:
            pass  # Non-critical, continue without rate limiting
        
        return None


class AuditMiddleware(MiddlewareMixin):
    """
    Audit logging middleware for medical compliance.
    Logs all data access and modifications.
    """
    
    # Paths that involve data access/modification
    AUDITABLE_API_PATHS = [
        '/api/tracking/',
        '/api/accounts/',
        '/api/notifications/',
    ]
    
    # Methods that modify data
    MODIFICATION_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']
    
    def process_request(self, request: HttpRequest) -> None:
        # Store request start time
        request._audit_start_time = time.time()
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        # Only audit API paths
        is_auditable = any(
            request.path.startswith(path) 
            for path in self.AUDITABLE_API_PATHS
        )
        
        if not is_auditable:
            return response
        
        # Skip failed requests (4xx, 5xx) except for security events
        if response.status_code >= 400:
            if response.status_code in [401, 403]:
                audit_logger.log_security_event(
                    'UNAUTHORIZED_ACCESS',
                    request,
                    {
                        'status_code': response.status_code,
                        'path': request.path,
                    }
                )
            return response
        
        # Log successful operations
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            if request.method in self.MODIFICATION_METHODS:
                audit_logger.log_data_modification(
                    user,
                    request,
                    resource=request.path,
                    action_type=request.method,
                )
            elif request.method == 'GET':
                # Only log specific data access, not list views
                if any(c.isdigit() for c in request.path.split('/')[-2:]):
                    audit_logger.log_data_access(
                        user,
                        request,
                        resource=request.path,
                    )
        
        return response


class RequestValidationMiddleware(MiddlewareMixin):
    """
    Validate and sanitize incoming requests.
    Block suspicious requests early.
    """
    
    # Maximum request body size (10MB)
    MAX_BODY_SIZE = 10 * 1024 * 1024
    
    # Suspicious patterns in request
    SUSPICIOUS_PATTERNS = [
        '../',  # Path traversal
        '..\\',  # Windows path traversal
        '\x00',  # Null byte
        '<script',  # XSS attempt
        'javascript:',  # XSS attempt
    ]
    
    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        # Check request size
        content_length = request.META.get('CONTENT_LENGTH')
        if content_length:
            try:
                if int(content_length) > self.MAX_BODY_SIZE:
                    return JsonResponse(
                        {'error': 'Request body too large'},
                        status=413
                    )
            except (ValueError, TypeError):
                pass
        
        # Check for suspicious patterns in path
        path_lower = request.path.lower()
        for pattern in self.SUSPICIOUS_PATTERNS:
            if pattern in path_lower:
                logger.warning(
                    f"Suspicious request blocked: {pattern}",
                    extra={'path': request.path, 'ip': get_client_ip(request)}
                )
                audit_logger.log_security_event(
                    'SUSPICIOUS_REQUEST',
                    request,
                    {'pattern': pattern, 'path': request.path}
                )
                return JsonResponse(
                    {'error': 'Invalid request'},
                    status=400
                )
        
        # Check for suspicious query parameters
        query_string = request.META.get('QUERY_STRING', '').lower()
        for pattern in self.SUSPICIOUS_PATTERNS:
            if pattern in query_string:
                logger.warning(
                    f"Suspicious query parameter blocked: {pattern}",
                    extra={'query': query_string, 'ip': get_client_ip(request)}
                )
                return JsonResponse(
                    {'error': 'Invalid request'},
                    status=400
                )
        
        return None


class AdminMFAEnforcementMiddleware(MiddlewareMixin):
    """Require MFA for staff/superusers before accessing protected pages."""

    ALLOWED_PATH_PREFIXES = [
        '/accounts/mfa/',
        '/accounts/logout/',
        '/accounts/login/',
        '/static/',
        '/favicon.ico',
    ]

    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return None

        if not (user.is_staff or user.is_superuser):
            return None

        if any(request.path.startswith(path) for path in self.ALLOWED_PATH_PREFIXES):
            return None

        try:
            mfa = getattr(user, 'mfa', None)
        except Exception:
            # Migration not applied yet or table missing
            return None
        if not mfa or not mfa.enabled:
            return redirect('accounts:mfa_setup')

        return None


class OnboardingMiddleware(MiddlewareMixin):
    """
    Redirect authenticated users who haven't completed onboarding.
    
    This ensures new users complete the onboarding flow before
    accessing the main application.
    """
    
    # Paths that don't require onboarding completion
    EXEMPT_PATHS = [
        '/accounts/onboarding/',
        '/accounts/logout/',
        '/accounts/login/',
        '/api/',
        '/admin/',
        '/static/',
        '/manifest.json',
        '/sw.js',
    ]
    
    def process_request(self, request: HttpRequest):
        # Skip for unauthenticated users
        if not request.user.is_authenticated:
            return None
        
        # Skip for exempt paths
        path = request.path
        for exempt in self.EXEMPT_PATHS:
            if path.startswith(exempt):
                return None
        
        # Check if user has completed onboarding
        if hasattr(request.user, 'profile') and not request.user.profile.onboarding_completed:
            from django.shortcuts import redirect
            # Determine which onboarding step to redirect to
            step = request.user.profile.onboarding_step
            step_urls = {
                0: 'accounts:onboarding_welcome',
                1: 'accounts:onboarding_welcome',
                2: 'accounts:onboarding_welcome',
                3: 'accounts:onboarding_gender',
                4: 'accounts:onboarding_gender',
                5: 'accounts:onboarding_diagnosis',
                6: 'accounts:onboarding_medication_status',
                7: 'accounts:onboarding_medication_select',
                8: 'accounts:onboarding_medication_details',
                9: 'accounts:onboarding_summary',
                10: 'accounts:onboarding_privacy',
                11: 'accounts:onboarding_reminders',
            }
            target = step_urls.get(step, 'accounts:onboarding_welcome')
            return redirect(target)
        
        return None
