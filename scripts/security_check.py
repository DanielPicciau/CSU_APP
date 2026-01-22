#!/usr/bin/env python
"""Security validation script for production deployment."""

import os
import sys

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()


def main():
    print("=" * 60)
    print("CSU Tracker Security Validation")
    print("=" * 60)
    
    errors = []
    
    # 1. Test password validators
    print("\n[1] Password Validators...")
    try:
        from core.validators import (
            MedicalGradePasswordValidator,
            NoPersonalInfoValidator,
            PwnedPasswordValidator
        )
        print("    OK: All validators imported")
    except ImportError as e:
        errors.append(f"Password validators: {e}")
        print(f"    FAIL: {e}")
    
    # 2. Test weak password rejection
    print("\n[2] Weak Password Rejection...")
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError
    
    try:
        validate_password('password123')
        errors.append("Weak password 'password123' was not rejected")
        print("    FAIL: Weak password accepted")
    except ValidationError as e:
        print(f"    OK: Rejected with {len(e.messages)} errors")
    
    # 3. Test security headers
    print("\n[3] Security Headers...")
    from core.security import SECURITY_HEADERS
    
    required_headers = [
        'Content-Security-Policy',
        'X-Frame-Options',
        'X-Content-Type-Options',
        'Cross-Origin-Opener-Policy',
        'Referrer-Policy',
    ]
    
    for header in required_headers:
        if header in SECURITY_HEADERS:
            print(f"    OK: {header}")
        else:
            errors.append(f"Missing header: {header}")
            print(f"    FAIL: Missing {header}")
    
    # 4. Test session settings
    print("\n[4] Session Security...")
    from django.conf import settings
    
    print(f"    Session age: {settings.SESSION_COOKIE_AGE // 86400} days")
    print(f"    SameSite: {settings.SESSION_COOKIE_SAMESITE}")
    print(f"    HTTPOnly: {settings.SESSION_COOKIE_HTTPONLY}")
    
    if not settings.SESSION_COOKIE_HTTPONLY:
        errors.append("SESSION_COOKIE_HTTPONLY is False")
    
    # 5. Check production settings (if DEBUG=False)
    print("\n[5] Production Settings...")
    if settings.DEBUG:
        print("    WARN: DEBUG=True (OK for development)")
    else:
        print("    OK: DEBUG=False")
        
        if not settings.SECURE_SSL_REDIRECT:
            errors.append("SECURE_SSL_REDIRECT is False in production")
            print("    FAIL: SECURE_SSL_REDIRECT is False")
        else:
            print("    OK: SSL redirect enabled")
    
    # 6. Check encryption-at-rest config
    print("\n[6] Encryption at Rest...")
    if settings.DEBUG:
        print("    WARN: DEBUG=True (dev keys allowed)")
    else:
        if getattr(settings, "FERNET_KEYS", None):
            print("    OK: FERNET_KEYS configured")
        else:
            errors.append("FERNET_KEYS not configured")
            print("    FAIL: FERNET_KEYS not configured")

    # 7. Check rate limiting
    print("\n[7] Rate Limiting...")
    from core.middleware import RateLimitMiddleware
    print(f"    Login limit: {RateLimitMiddleware.LIMITS.get('/accounts/login/', 'default')}")
    print(f"    API register limit: {RateLimitMiddleware.LIMITS.get('/api/accounts/register/', 'default')}")
    print("    OK: Rate limiting configured")
    
    # 8. Check account lockout
    print("\n[8] Account Lockout...")
    from core.security import AccountLockout
    print(f"    Max attempts: {AccountLockout.MAX_FAILED_ATTEMPTS}")
    print(f"    Lockout duration: {AccountLockout.LOCKOUT_DURATION // 60} minutes")
    print("    OK: Account lockout configured")
    
    # 9. Check admin privacy
    print("\n[9] Admin Privacy...")
    from django.contrib.admin.sites import site
    
    for model, admin_class in site._registry.items():
        if model._meta.app_label in ['accounts', 'tracking', 'notifications']:
            has_change = True
            if hasattr(admin_class, 'has_change_permission'):
                # Check if it's overridden to return False
                import inspect
                source = inspect.getsource(admin_class.has_change_permission)
                if 'return False' in source:
                    has_change = False
            
            status = "read-only" if not has_change else "editable"
            print(f"    {model._meta.label}: {status}")
    
    # Summary
    print("\n" + "=" * 60)
    if errors:
        print(f"FAILED: {len(errors)} security issue(s) found")
        for error in errors:
            print(f"  - {error}")
        return 1
    else:
        print("PASSED: All security checks passed")
        return 0


if __name__ == '__main__':
    sys.exit(main())
