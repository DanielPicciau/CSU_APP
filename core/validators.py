"""
Enhanced password validator for medical-grade security.
"""

import hashlib
import logging

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from core.security import PasswordPolicy

logger = logging.getLogger('security')


class PwnedPasswordValidator:
    """
    Check if password has been exposed in known data breaches.
    Uses the Have I Been Pwned API with k-anonymity (only sends first 5 chars of hash).
    """
    
    def validate(self, password, user=None):
        # Check against HIBP API using k-anonymity
        sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
        prefix = sha1_hash[:5]
        suffix = sha1_hash[5:]
        
        try:
            import urllib.request
            import urllib.error
            
            url = f'https://api.pwnedpasswords.com/range/{prefix}'
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'CSU-Tracker-PasswordCheck',
                    'Add-Padding': 'true',  # Prevent response length timing attacks
                }
            )
            
            with urllib.request.urlopen(req, timeout=3) as response:
                hash_suffixes = response.read().decode('utf-8')
                
            for line in hash_suffixes.splitlines():
                if ':' in line:
                    hash_suffix, count = line.split(':')
                    if hash_suffix == suffix:
                        breach_count = int(count)
                        if breach_count > 0:
                            logger.warning(
                                f"Password found in {breach_count} breaches (hash prefix: {prefix})"
                            )
                            raise ValidationError(
                                _(
                                    "This password has appeared in known data breaches. "
                                    "Please choose a different password for your security."
                                ),
                                code='password_pwned',
                            )
        except (urllib.error.URLError, TimeoutError, OSError):
            # If API is unavailable, allow password (fail open for availability)
            # but log the failure for monitoring
            logger.warning("HIBP API unavailable - password breach check skipped")
            pass
    
    def get_help_text(self):
        return _("Your password cannot be one that has appeared in known data breaches.")


class MedicalGradePasswordValidator:
    """
    Validate password meets medical-grade security requirements.
    
    Requirements:
    - Minimum 12 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    - Not a commonly used password
    - Does not contain user information
    """
    
    def validate(self, password, user=None):
        is_valid, errors = PasswordPolicy.validate(password, user)
        if not is_valid:
            raise ValidationError(
                errors,
                code='password_policy_violation',
            )
    
    def get_help_text(self):
        return _(
            "Your password must be at least 12 characters long and contain "
            "at least one uppercase letter, one lowercase letter, one digit, "
            "and one special character (!@#$%^&*()_+-=[]{}|;:',.<>?/)."
        )


class NoPersonalInfoValidator:
    """Ensure password doesn't contain personal information."""
    
    def validate(self, password, user=None):
        if user is None:
            return
        
        password_lower = password.lower()
        
        # Check email
        if hasattr(user, 'email') and user.email:
            email_parts = user.email.lower().split('@')[0]
            if len(email_parts) >= 3 and email_parts in password_lower:
                raise ValidationError(
                    _("Your password cannot contain parts of your email address."),
                    code='password_contains_email',
                )
        
        # Check name
        if hasattr(user, 'first_name') and user.first_name:
            if len(user.first_name) >= 3 and user.first_name.lower() in password_lower:
                raise ValidationError(
                    _("Your password cannot contain your name."),
                    code='password_contains_name',
                )
        
        if hasattr(user, 'last_name') and user.last_name:
            if len(user.last_name) >= 3 and user.last_name.lower() in password_lower:
                raise ValidationError(
                    _("Your password cannot contain your name."),
                    code='password_contains_name',
                )
    
    def get_help_text(self):
        return _("Your password cannot contain your email address or name.")
