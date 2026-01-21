"""
Models for CSU tracking.
"""

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class DailyEntry(models.Model):
    """
    Daily CSU score entry for a user.
    
    The UAS7 (Urticaria Activity Score 7) is calculated by summing daily scores
    over 7 days. Each daily score consists of:
    - Itch severity (0-3)
    - Hive count (0-3)
    Combined daily score: 0-6, weekly UAS7: 0-42
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="daily_entries",
    )
    
    date = models.DateField(
        help_text="Date of the entry (user's local date)",
    )
    
    # Combined score (0-6 per day, or use 0-42 for weekly flexibility)
    score = models.PositiveIntegerField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(settings.CSU_MAX_SCORE),
        ],
        help_text="Total CSU score for this day",
    )
    
    # Component scores (optional, for detailed tracking)
    itch_score = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(3)],
        help_text="Itch severity: 0=None, 1=Mild, 2=Moderate, 3=Severe",
    )
    
    hive_count_score = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(3)],
        help_text="Hive count: 0=None, 1=Mild (<20), 2=Moderate (20-50), 3=Severe (>50)",
    )
    
    # Additional tracking
    notes = models.TextField(
        blank=True,
        default="",
        help_text="Optional notes about the day",
    )
    
    took_antihistamine = models.BooleanField(
        default=False,
        help_text="Whether antihistamine was taken",
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "daily entry"
        verbose_name_plural = "daily entries"
        ordering = ["-date"]
        # Ensure one entry per user per day
        constraints = [
            models.UniqueConstraint(
                fields=["user", "date"],
                name="unique_user_date_entry",
            )
        ]
        indexes = [
            models.Index(fields=["user", "date"]),
            models.Index(fields=["user", "-date"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} - {self.date}: {self.score}"

    def save(self, *args, **kwargs):
        """Auto-calculate combined score if component scores are provided."""
        if self.itch_score is not None and self.hive_count_score is not None:
            # If individual scores are provided, use them if no total score set
            if self.score == 0 or self.score is None:
                self.score = self.itch_score + self.hive_count_score
        super().save(*args, **kwargs)
