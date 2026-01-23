"""
Custom User model and Profile for CSU Tracker.
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.sessions.models import Session
from django.db import models
from django.utils import timezone
from django.utils.crypto import salted_hmac

from core.fields import EncryptedCharField, EncryptedDateField



class UserManager(BaseUserManager):
    """Custom user manager that uses email as the unique identifier."""

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        """Create and save a regular user with the given email and password."""
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        """Create and save a superuser with the given email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user model that uses email instead of username."""

    username = None
    email = models.EmailField("email address", unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self) -> str:
        return self.email


# Score scale choices
# Score scale choices
SCORE_SCALE_CHOICES = [
    ("0-6", "Combined UAS (0-6)"),
    ("separate", "Separate Itch & Hive (0-3 each)"),
]

# Gender choices for onboarding
GENDER_CHOICES = [
    ("male", "Male"),
    ("female", "Female"),
    ("non_binary", "Non-binary"),
    ("prefer_not_to_say", "Prefer not to say"),
]

# CSU diagnosis status choices
CSU_DIAGNOSIS_CHOICES = [
    ("yes", "Yes"),
    ("no", "No"),
    ("unsure", "Unsure"),
]

# Medication status choices
MEDICATION_STATUS_CHOICES = [
    ("yes", "Yes"),
    ("no", "No"),
    ("prefer_not_to_say", "Prefer not to say"),
]

# Medication type choices
MEDICATION_TYPE_CHOICES = [
    ("antihistamine", "Antihistamine"),
    ("biologic", "Biologic / Injectable"),
    ("other", "Other"),
]

# Common CSU medications (curated list)
# Note: This is informational only, not medical advice
COMMON_MEDICATIONS = [
    # Second-generation antihistamines (most common for CSU)
    ("fexofenadine", "Fexofenadine (Allegra)", "antihistamine"),
    ("cetirizine", "Cetirizine (Zyrtec)", "antihistamine"),
    ("loratadine", "Loratadine (Claritin)", "antihistamine"),
    ("desloratadine", "Desloratadine (Clarinex)", "antihistamine"),
    ("levocetirizine", "Levocetirizine (Xyzal)", "antihistamine"),
    ("bilastine", "Bilastine (Blexten)", "antihistamine"),
    ("rupatadine", "Rupatadine (Rupafin)", "antihistamine"),
    # Biologics
    ("omalizumab", "Omalizumab (Xolair)", "biologic"),
    ("ligelizumab", "Ligelizumab", "biologic"),
    # Other
    ("other", "Other medication", "other"),
]

# Injection frequency choices
INJECTION_FREQUENCY_CHOICES = [
    ("every_2_weeks", "Every 2 weeks"),
    ("every_4_weeks", "Every 4 weeks"),
    ("every_6_weeks", "Every 6 weeks"),
    ("every_8_weeks", "Every 8 weeks"),
    ("as_needed", "As needed"),
    ("other", "Other schedule"),
]


class Profile(models.Model):
    """Extended user profile for CSU tracking preferences."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    
    # Personal info
    display_name = EncryptedCharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Optional name for personalization",
    )
    
    # Onboarding fields
    date_of_birth = EncryptedDateField(
        null=True,
        blank=True,
        help_text="User's date of birth",
    )
    
    age = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="User's age (calculated from DOB)",
    )
    
    gender = EncryptedCharField(
        max_length=20,
        choices=GENDER_CHOICES,
        blank=True,
        default="",
        help_text="How user describes their gender",
    )
    
    csu_diagnosis = EncryptedCharField(
        max_length=10,
        choices=CSU_DIAGNOSIS_CHOICES,
        blank=True,
        default="",
        help_text="Whether user has been diagnosed with CSU",
    )
    
    # Treatment context (metadata only - NOT medical advice)
    has_prescribed_medication = EncryptedCharField(
        max_length=20,
        choices=MEDICATION_STATUS_CHOICES,
        blank=True,
        default="",
        help_text="Whether user has been prescribed medication for their condition",
    )
    
    onboarding_completed = models.BooleanField(
        default=False,
        help_text="Whether user has completed onboarding",
    )
    
    onboarding_step = models.PositiveIntegerField(
        default=0,
        help_text="Current onboarding step (0 = not started)",
    )
    
    # Display preferences
    date_format = models.CharField(
        max_length=20,
        default="YYYY-MM-DD",
        help_text="Preferred date display format",
    )
    
    preferred_score_scale = models.CharField(
        max_length=20,
        choices=SCORE_SCALE_CHOICES,
        default="0-6",
        help_text="Preferred score input method",
    )
    
    # Tracking preferences
    default_timezone = models.CharField(
        max_length=50,
        default="Europe/London",
        help_text="IANA timezone string for the user",
    )
    
    # Privacy settings
    allow_data_collection = models.BooleanField(
        default=True,
        help_text="Allow anonymous usage analytics",
    )
    
    # Privacy consent (explicit consent for data processing)
    privacy_consent_given = models.BooleanField(
        default=False,
        help_text="User has explicitly consented to data storage and processing",
    )
    
    privacy_consent_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When privacy consent was given",
    )
    
    # Account status
    account_deletion_requested = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When account deletion was requested (30-day grace period)",
    )
    
    # Account pause (Right to Restrict Processing - GDPR Article 18)
    account_paused = models.BooleanField(
        default=False,
        help_text="Account is paused - data retained but not processed",
    )
    
    account_paused_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the account was paused",
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "profile"
        verbose_name_plural = "profiles"

    def __str__(self) -> str:
        return f"Profile for {self.user.email}"
    
    @property
    def display_name_or_email(self) -> str:
        """Return display name if set, otherwise email username part."""
        if self.display_name:
            return self.display_name
        return self.user.email.split("@")[0]
    
    @property
    def initials(self) -> str:
        """Return initials for avatar."""
        if self.display_name:
            parts = self.display_name.split()
            if len(parts) >= 2:
                return (parts[0][0] + parts[-1][0]).upper()
            return self.display_name[0].upper()
        return self.user.email[0].upper()


class UserMFA(models.Model):
    """TOTP-based MFA configuration for a user."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="mfa",
    )

    secret = EncryptedCharField(
        max_length=64,
        help_text="Base32-encoded TOTP secret",
    )

    enabled = models.BooleanField(
        default=False,
        help_text="Whether MFA is enabled for this user",
    )

    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When MFA was confirmed",
    )

    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last successful MFA verification",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "MFA configuration"
        verbose_name_plural = "MFA configurations"

    def __str__(self) -> str:
        return f"MFA for {self.user.email} ({'enabled' if self.enabled else 'disabled'})"


class PasswordResetToken(models.Model):
    """Single-use password reset tokens stored hashed."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )

    token_hash = models.CharField(
        max_length=64,
        help_text="SHA256-based token hash",
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    requested_ip = models.CharField(max_length=45, blank=True, default="")
    requested_user_agent = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        verbose_name = "password reset token"
        verbose_name_plural = "password reset tokens"
        indexes = [
            models.Index(fields=["user", "token_hash"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"Password reset token for {self.user.email}"

    @staticmethod
    def hash_token(token: str) -> str:
        return salted_hmac("password-reset", token).hexdigest()

    def is_valid(self) -> bool:
        return self.used_at is None and self.expires_at >= timezone.now()

    def mark_used(self) -> None:
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])


# Signal to create profile when user is created
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a Profile instance when a new User is created."""
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the Profile instance when the User is saved."""
    if hasattr(instance, "profile"):
        instance.profile.save()


@receiver(pre_save, sender=User)
def stash_user_privilege(sender, instance, **kwargs):
    """Store previous privilege flags for comparison after save."""
    if not instance.pk:
        return
    try:
        previous = sender.objects.get(pk=instance.pk)
        instance._prev_is_staff = previous.is_staff
        instance._prev_is_superuser = previous.is_superuser
    except Exception:
        return


@receiver(post_save, sender=User)
def invalidate_sessions_on_privilege_change(sender, instance, created, **kwargs):
    """Invalidate sessions when staff/superuser status changes."""
    if created:
        return
    prev_staff = getattr(instance, "_prev_is_staff", instance.is_staff)
    prev_superuser = getattr(instance, "_prev_is_superuser", instance.is_superuser)
    if prev_staff == instance.is_staff and prev_superuser == instance.is_superuser:
        return

    try:
        sessions = Session.objects.filter(expire_date__gte=timezone.now())
        for session in sessions:
            try:
                session_data = session.get_decoded()
                if session_data.get('_auth_user_id') == str(instance.pk):
                    session.delete()
            except Exception:
                continue
    except Exception:
        pass


class UserMedication(models.Model):
    """
    User-reported medication context for trend visualization.
    
    IMPORTANT: This is user-entered contextual metadata only.
    - NOT a prescription or medical record
    - NOT used for treatment recommendations
    - Used solely to help users correlate their symptom patterns
    
    All fields are optional and user-controlled.
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="medications",
    )
    
    # Medication identification
    medication_key = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Key from COMMON_MEDICATIONS list (e.g., 'fexofenadine')",
    )
    
    custom_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="User-entered medication name (if not in list)",
    )
    
    medication_type = models.CharField(
        max_length=20,
        choices=MEDICATION_TYPE_CHOICES,
        default="other",
        help_text="Category of medication",
    )
    
    # Antihistamine-specific context (optional)
    dose_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Dose amount (user-reported, not verified)",
    )
    
    dose_unit = models.CharField(
        max_length=20,
        blank=True,
        default="mg",
        help_text="Dose unit (e.g., mg, ml)",
    )
    
    frequency_per_day = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="How many times per day (user-reported)",
    )
    
    # Injectable/biologic-specific context (optional)
    last_injection_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of last injection (user-reported)",
    )
    
    injection_frequency = models.CharField(
        max_length=20,
        choices=INJECTION_FREQUENCY_CHOICES,
        blank=True,
        default="",
        help_text="Typical injection schedule",
    )
    
    # Status
    is_current = models.BooleanField(
        default=True,
        help_text="Whether user is currently taking this",
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "user medication"
        verbose_name_plural = "user medications"
        ordering = ["-is_current", "-updated_at"]
    
    def __str__(self) -> str:
        """Privacy-safe string representation - NO medication details exposed."""
        # PRIVACY: Do not expose medication name in string representation
        # This prevents leaking health data through admin, logs, etc.
        return f"Medication record #{self.pk} - {self.user.email}"
    
    @property
    def display_name(self) -> str:
        """Return human-readable medication name."""
        if self.custom_name:
            return self.custom_name
        # Look up from COMMON_MEDICATIONS
        for key, label, _ in COMMON_MEDICATIONS:
            if key == self.medication_key:
                return label
        return self.medication_key or "Unknown"
    
    @property
    def is_antihistamine(self) -> bool:
        return self.medication_type == "antihistamine"
    
    @property
    def is_biologic(self) -> bool:
        return self.medication_type == "biologic"
