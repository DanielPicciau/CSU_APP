"""
Security configurations and utilities for medical-grade application.
"""

import hashlib
import logging
import re
from functools import wraps
from typing import Optional

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.utils import timezone

logger = logging.getLogger('security')


# =============================================================================
# ACCOUNT LOCKOUT
# =============================================================================

class AccountLockout:
    """
    Account lockout mechanism to prevent brute force attacks.
    
    After MAX_FAILED_ATTEMPTS failed login attempts, the account is locked
    for LOCKOUT_DURATION seconds.
    """
    
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION = 900  # 15 minutes in seconds
    
    @classmethod
    def get_lockout_key(cls, identifier: str) -> str:
        """Get cache key for lockout tracking."""
        return f"account_lockout:{identifier}"
    
    @classmethod
    def get_attempts_key(cls, identifier: str) -> str:
        """Get cache key for failed attempts counter."""
        return f"failed_attempts:{identifier}"
    
    @classmethod
    def is_locked(cls, identifier: str) -> bool:
        """Check if an identifier (email/IP) is currently locked out."""
        lockout_key = cls.get_lockout_key(identifier)
        return cache.get(lockout_key) is not None
    
    @classmethod
    def get_lockout_remaining(cls, identifier: str) -> int:
        """Get remaining lockout time in seconds."""
        lockout_key = cls.get_lockout_key(identifier)
        lockout_time = cache.get(lockout_key)
        if lockout_time:
            remaining = cls.LOCKOUT_DURATION - (timezone.now().timestamp() - lockout_time)
            return max(0, int(remaining))
        return 0
    
    @classmethod
    def record_failed_attempt(cls, identifier: str) -> tuple[int, bool]:
        """
        Record a failed login attempt.
        
        Returns:
            tuple: (attempts_count, is_now_locked)
        """
        attempts_key = cls.get_attempts_key(identifier)
        lockout_key = cls.get_lockout_key(identifier)
        
        # Increment attempts
        attempts = cache.get(attempts_key, 0) + 1
        cache.set(attempts_key, attempts, cls.LOCKOUT_DURATION)
        
        # Check if should lock
        if attempts >= cls.MAX_FAILED_ATTEMPTS:
            cache.set(lockout_key, timezone.now().timestamp(), cls.LOCKOUT_DURATION)
            logger.warning(
                f"Account locked due to {attempts} failed attempts",
                extra={'identifier': hashlib.sha256(identifier.encode()).hexdigest()[:16]}
            )
            return attempts, True
        
        return attempts, False
    
    @classmethod
    def reset_attempts(cls, identifier: str) -> None:
        """Reset failed attempts after successful login."""
        attempts_key = cls.get_attempts_key(identifier)
        lockout_key = cls.get_lockout_key(identifier)
        cache.delete(attempts_key)
        cache.delete(lockout_key)


# =============================================================================
# RATE LIMITING
# =============================================================================

class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    pass


# Known private/internal IP ranges (for filtering X-Forwarded-For)
PRIVATE_IP_PREFIXES = (
    '10.',
    '172.16.', '172.17.', '172.18.', '172.19.',
    '172.20.', '172.21.', '172.22.', '172.23.',
    '172.24.', '172.25.', '172.26.', '172.27.',
    '172.28.', '172.29.', '172.30.', '172.31.',
    '192.168.',
    '127.',
    '::1',
    'fc00:',
    'fe80:',
)


def is_private_ip(ip: str) -> bool:
    """Check if an IP address is private/internal."""
    if not ip:
        return True
    ip_lower = ip.lower().strip()
    if ip_lower in ('localhost', '', 'unknown'):
        return True
    return any(ip_lower.startswith(prefix) for prefix in PRIVATE_IP_PREFIXES)


def get_client_ip(request) -> str:
    """
    Extract client IP from request, handling proxies securely.
    
    Security Note: X-Forwarded-For can be spoofed by clients.
    In production, configure your proxy/load balancer to:
    1. Strip any existing X-Forwarded-For from client
    2. Add the real client IP as X-Forwarded-For
    
    Strategy:
    - For PaaS platforms (PythonAnywhere/Railway/Heroku), the first IP
      in X-Forwarded-For is set by the platform's load balancer.
    - We validate IPs and skip private/internal addresses.
    - Maximum of 5 hops to prevent header injection attacks.
    """
    # Check if we're behind a trusted proxy
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Parse and limit to prevent header injection attacks
        ips = [ip.strip() for ip in x_forwarded_for.split(',')][:5]  # Max 5 hops
        
        # Return first non-private IP (usually the client IP set by edge proxy)
        for ip in ips:
            if ip and not is_private_ip(ip):
                # Basic IP format validation
                if '.' in ip or ':' in ip:  # IPv4 or IPv6
                    return ip
        
        # If all are private, return the first one (internal request)
        if ips and ips[0]:
            return ips[0]
    
    # Fallback to REMOTE_ADDR
    return request.META.get('REMOTE_ADDR', 'unknown')


def rate_limit(key_prefix: str, max_requests: int, window_seconds: int):
    """
    Rate limiting decorator for views.
    
    Args:
        key_prefix: Prefix for the cache key
        max_requests: Maximum number of requests allowed
        window_seconds: Time window in seconds
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Create unique key based on IP and user
            ip = get_client_ip(request)
            user_id = request.user.id if request.user.is_authenticated else 'anon'
            cache_key = f"ratelimit:{key_prefix}:{ip}:{user_id}"
            
            # Get current count
            current = cache.get(cache_key, 0)
            
            if current >= max_requests:
                logger.warning(
                    f"Rate limit exceeded for {key_prefix}",
                    extra={
                        'ip': ip,
                        'user_id': user_id,
                        'path': request.path,
                    }
                )
                return JsonResponse(
                    {'error': 'Rate limit exceeded. Please try again later.'},
                    status=429
                )
            
            # Increment counter
            cache.set(cache_key, current + 1, window_seconds)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# INPUT VALIDATION & SANITIZATION
# =============================================================================

class InputValidator:
    """Validate and sanitize user inputs."""
    
    # Patterns for validation
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    SAFE_TEXT_PATTERN = re.compile(r'^[\w\s.,!?\'"-]*$', re.UNICODE)
    
    # Dangerous patterns to block
    DANGEROUS_PATTERNS = [
        re.compile(r'<script', re.IGNORECASE),
        re.compile(r'javascript:', re.IGNORECASE),
        re.compile(r'on\w+\s*=', re.IGNORECASE),  # onclick, onload, etc.
        re.compile(r'<\s*iframe', re.IGNORECASE),
        re.compile(r'<\s*object', re.IGNORECASE),
        re.compile(r'<\s*embed', re.IGNORECASE),
    ]
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 1000) -> str:
        """Sanitize a string input."""
        if not isinstance(value, str):
            return str(value)[:max_length]
        
        # Truncate to max length
        value = value[:max_length]
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern.search(value):
                logger.warning(f"Dangerous pattern detected and removed: {pattern.pattern}")
                value = pattern.sub('', value)
        
        return value.strip()
    
    @classmethod
    def validate_email(cls, email: str) -> bool:
        """Validate email format."""
        if not email or not isinstance(email, str):
            return False
        return bool(cls.EMAIL_PATTERN.match(email))
    
    @classmethod
    def validate_score(cls, score: int, min_val: int = 0, max_val: int = 42) -> bool:
        """Validate CSU score is within valid range."""
        try:
            score = int(score)
            return min_val <= score <= max_val
        except (ValueError, TypeError):
            return False
    
    @classmethod
    def sanitize_notes(cls, notes: str, max_length: int = 2000) -> str:
        """Sanitize notes field - allow more characters but still safe."""
        notes = cls.sanitize_string(notes, max_length)
        # Remove any remaining HTML-like content
        notes = re.sub(r'<[^>]+>', '', notes)
        return notes


# =============================================================================
# AUDIT LOGGING
# =============================================================================

class AuditLogger:
    """
    Audit logging for medical-grade compliance.
    Logs all significant user actions and data access.
    """
    
    def __init__(self):
        self.logger = logging.getLogger('audit')
    
    def log_action(
        self,
        action: str,
        user,
        request,
        details: Optional[dict] = None,
        success: bool = True,
    ):
        """Log an auditable action."""
        log_data = {
            'timestamp': timezone.now().isoformat(),
            'action': action,
            'user_id': user.id if user and user.is_authenticated else None,
            'user_email': user.email if user and user.is_authenticated else None,
            'ip_address': get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
            'path': request.path,
            'method': request.method,
            'success': success,
            'details': details or {},
        }
        
        if success:
            self.logger.info(f"AUDIT: {action}", extra=log_data)
        else:
            self.logger.warning(f"AUDIT FAILED: {action}", extra=log_data)
    
    def log_login(self, user, request, success: bool = True):
        """Log login attempt."""
        self.log_action('LOGIN', user, request, success=success)
    
    def log_logout(self, user, request):
        """Log logout."""
        self.log_action('LOGOUT', user, request)
    
    def log_data_access(self, user, request, resource: str, resource_id=None):
        """Log data access."""
        self.log_action(
            'DATA_ACCESS',
            user,
            request,
            details={'resource': resource, 'resource_id': resource_id}
        )
    
    def log_data_modification(
        self,
        user,
        request,
        resource: str,
        resource_id=None,
        action_type: str = 'UPDATE',
        changes: Optional[dict] = None,
    ):
        """Log data modification."""
        self.log_action(
            f'DATA_{action_type}',
            user,
            request,
            details={
                'resource': resource,
                'resource_id': resource_id,
                'changes': changes,
            }
        )
    
    def log_security_event(
        self,
        event_type: str,
        request,
        details: Optional[dict] = None,
    ):
        """Log security-related events."""
        user = getattr(request, 'user', None)
        self.log_action(
            f'SECURITY_{event_type}',
            user,
            request,
            details=details,
            success=False,
        )


# Global audit logger instance
audit_logger = AuditLogger()


# =============================================================================
# PASSWORD SECURITY
# =============================================================================

class PasswordPolicy:
    """Enforce strong password policy for medical application."""
    
    MIN_LENGTH = 12
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = True
    SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:',.<>?/"
    
    # Common weak passwords to block
    BLOCKED_PASSWORDS = {
        'password', 'password123', '12345678', 'qwerty123',
        'letmein', 'welcome', 'admin123', 'changeme',
    }
    
    @classmethod
    def validate(cls, password: str, user=None) -> tuple[bool, list[str]]:
        """
        Validate password against policy.
        
        Returns:
            tuple: (is_valid, list of error messages)
        """
        errors = []
        
        if len(password) < cls.MIN_LENGTH:
            errors.append(f"Password must be at least {cls.MIN_LENGTH} characters long.")
        
        if cls.REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter.")
        
        if cls.REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter.")
        
        if cls.REQUIRE_DIGIT and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one number.")
        
        if cls.REQUIRE_SPECIAL and not any(c in cls.SPECIAL_CHARS for c in password):
            errors.append(f"Password must contain at least one special character ({cls.SPECIAL_CHARS}).")
        
        if password.lower() in cls.BLOCKED_PASSWORDS:
            errors.append("This password is too common. Please choose a stronger password.")
        
        # Check if password contains user info
        if user:
            email_part = user.email.split('@')[0].lower() if hasattr(user, 'email') else ''
            if email_part and email_part in password.lower():
                errors.append("Password cannot contain your email address.")
        
        return len(errors) == 0, errors


# =============================================================================
# DATA ENCRYPTION HELPERS
# =============================================================================

def hash_sensitive_data(data: str) -> str:
    """Create a SHA-256 hash of sensitive data for logging (never log raw PII)."""
    return hashlib.sha256(data.encode()).hexdigest()[:16]


# =============================================================================
# SECURITY HEADERS
# =============================================================================

SECURITY_HEADERS = {
    # Prevent clickjacking
    'X-Frame-Options': 'DENY',
    
    # Prevent MIME type sniffing
    'X-Content-Type-Options': 'nosniff',
    
    # Enable XSS filter (legacy but still helps older browsers)
    'X-XSS-Protection': '1; mode=block',
    
    # Referrer policy - strict for health data privacy
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    
    # Permissions policy - disable unnecessary browser features
    'Permissions-Policy': (
        'geolocation=(), '
        'microphone=(), '
        'camera=(), '
        'payment=(), '
        'usb=(), '
        'magnetometer=(), '
        'gyroscope=(), '
        'accelerometer=()'
    ),
    
    # Cross-Origin policies for additional isolation
    'Cross-Origin-Opener-Policy': 'same-origin',
    'Cross-Origin-Resource-Policy': 'same-origin',
    
    # Content Security Policy
    # Note: 'unsafe-inline' is required for inline scripts and styles in templates
    # TODO: Implement nonce-based CSP for better security
    'Content-Security-Policy': (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://unpkg.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' https:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "upgrade-insecure-requests;"
    ),
}
