"""
Security middleware for medical-grade application.
"""

import logging
import time
from typing import Callable

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin

from .security import (
    SECURITY_HEADERS,
    get_client_ip,
    audit_logger,
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
        '/api/accounts/register/': (3, 60),
        '/api/accounts/token/': (10, 60),
        '/api/': (100, 60),
        'default': (200, 60),
    }
    
    # Paths to exclude from rate limiting
    EXCLUDED_PATHS = [
        '/static/',
        '/favicon.ico',
        '/manifest.json',
        '/sw.js',
        '/notifications/cron/',  # External cron service
    ]
    
    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        # Skip rate limiting in tests
        if getattr(settings, 'TESTING', False):
            return None
        
        # Skip excluded paths
        for excluded in self.EXCLUDED_PATHS:
            if request.path.startswith(excluded):
                return None
        
        # Determine rate limit for this path
        max_requests, window = self.LIMITS['default']
        for path_prefix, limits in self.LIMITS.items():
            if path_prefix != 'default' and request.path.startswith(path_prefix):
                max_requests, window = limits
                break
        
        # Create cache key
        ip = get_client_ip(request)
        user_id = request.user.id if hasattr(request, 'user') and request.user.is_authenticated else 'anon'
        cache_key = f"ratelimit:global:{request.path}:{ip}:{user_id}"
        
        # Check rate limit
        current = cache.get(cache_key, 0)
        
        if current >= max_requests:
            logger.warning(
                f"Rate limit exceeded: {request.path}",
                extra={
                    'ip': ip,
                    'path': request.path,
                    'limit': max_requests,
                }
            )
            audit_logger.log_security_event(
                'RATE_LIMIT_EXCEEDED',
                request,
                {'path': request.path, 'limit': max_requests}
            )
            return JsonResponse(
                {
                    'error': 'Rate limit exceeded. Please try again later.',
                    'retry_after': window,
                },
                status=429,
                headers={'Retry-After': str(window)}
            )
        
        # Increment counter
        cache.set(cache_key, current + 1, window)
        
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
