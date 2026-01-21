"""
Custom User model and Profile for CSU Tracker.
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


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
SCORE_SCALE_CHOICES = [
    ("0-6", "Combined UAS (0-6)"),
    ("separate", "Separate Itch & Hive (0-3 each)"),
]


class Profile(models.Model):
    """Extended user profile for CSU tracking preferences."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    
    # Personal info
    display_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Optional name for personalization",
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
        default="America/New_York",
        help_text="IANA timezone string for the user",
    )
    
    # Privacy settings
    allow_data_collection = models.BooleanField(
        default=True,
        help_text="Allow anonymous usage analytics",
    )
    
    # Account status
    account_deletion_requested = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When account deletion was requested (30-day grace period)",
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


# Signal to create profile when user is created
from django.db.models.signals import post_save
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
