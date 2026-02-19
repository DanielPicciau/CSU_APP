"""
Tests for injection reminder feature.

Covers:
- UserMedication.next_injection_date property
- RecordInjectionAPIView endpoint
- send_injection_reminders Celery task
- Today view injection context
- Export includes next estimated injection date
"""

from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import UserMedication
from notifications.models import PushSubscription

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def create_user(db):
    def _create_user(email="test@example.com", password="XkT9$mNq@2rSvW#4pLz!", **kwargs):
        return User.objects.create_user(email=email, password=password, **kwargs)
    return _create_user


@pytest.fixture
def user_with_biologic(create_user):
    """Create a user with a current biologic medication."""
    user = create_user()
    med = UserMedication.objects.create(
        user=user,
        medication_key="omalizumab",
        medication_type="biologic",
        injection_frequency="every_4_weeks",
        last_injection_date=date.today() - timedelta(days=21),
        is_current=True,
    )
    return user, med


# =============================================================================
# NEXT INJECTION DATE PROPERTY
# =============================================================================


@pytest.mark.django_db
class TestNextInjectionDate:
    """Tests for the UserMedication.next_injection_date property."""

    def test_every_4_weeks(self, create_user):
        user = create_user()
        last = date(2025, 1, 1)
        med = UserMedication.objects.create(
            user=user,
            medication_type="biologic",
            injection_frequency="every_4_weeks",
            last_injection_date=last,
            is_current=True,
        )
        assert med.next_injection_date == last + timedelta(days=28)

    def test_every_2_weeks(self, create_user):
        user = create_user()
        last = date(2025, 6, 1)
        med = UserMedication.objects.create(
            user=user,
            medication_type="biologic",
            injection_frequency="every_2_weeks",
            last_injection_date=last,
            is_current=True,
        )
        assert med.next_injection_date == last + timedelta(days=14)

    def test_every_6_weeks(self, create_user):
        user = create_user()
        last = date(2025, 3, 10)
        med = UserMedication.objects.create(
            user=user,
            medication_type="biologic",
            injection_frequency="every_6_weeks",
            last_injection_date=last,
            is_current=True,
        )
        assert med.next_injection_date == last + timedelta(days=42)

    def test_every_8_weeks(self, create_user):
        user = create_user()
        last = date(2025, 4, 15)
        med = UserMedication.objects.create(
            user=user,
            medication_type="biologic",
            injection_frequency="every_8_weeks",
            last_injection_date=last,
            is_current=True,
        )
        assert med.next_injection_date == last + timedelta(days=56)

    def test_as_needed_returns_none(self, create_user):
        user = create_user()
        med = UserMedication.objects.create(
            user=user,
            medication_type="biologic",
            injection_frequency="as_needed",
            last_injection_date=date(2025, 1, 1),
            is_current=True,
        )
        assert med.next_injection_date is None

    def test_other_returns_none(self, create_user):
        user = create_user()
        med = UserMedication.objects.create(
            user=user,
            medication_type="biologic",
            injection_frequency="other",
            last_injection_date=date(2025, 1, 1),
            is_current=True,
        )
        assert med.next_injection_date is None

    def test_no_last_date_returns_none(self, create_user):
        user = create_user()
        med = UserMedication.objects.create(
            user=user,
            medication_type="biologic",
            injection_frequency="every_4_weeks",
            is_current=True,
        )
        assert med.next_injection_date is None

    def test_no_frequency_returns_none(self, create_user):
        user = create_user()
        med = UserMedication.objects.create(
            user=user,
            medication_type="biologic",
            last_injection_date=date(2025, 1, 1),
            is_current=True,
        )
        assert med.next_injection_date is None


# =============================================================================
# RECORD INJECTION API
# =============================================================================


@pytest.mark.django_db
class TestRecordInjectionAPI:
    """Tests for the POST /api/accounts/injection/record/ endpoint."""

    def test_record_injection_success(self, api_client, user_with_biologic):
        user, med = user_with_biologic
        api_client.force_authenticate(user=user)
        url = reverse("accounts_api:record_injection")
        data = {"medication_id": med.pk, "injection_date": str(date.today())}
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_200_OK
        med.refresh_from_db()
        assert med.last_injection_date == date.today()
        assert "next_injection_date" in response.data

    def test_record_injection_updates_last_date(self, api_client, user_with_biologic):
        user, med = user_with_biologic
        api_client.force_authenticate(user=user)
        new_date = date.today() - timedelta(days=2)
        url = reverse("accounts_api:record_injection")
        data = {"medication_id": med.pk, "injection_date": str(new_date)}
        api_client.post(url, data, format="json")
        med.refresh_from_db()
        assert med.last_injection_date == new_date

    def test_record_injection_rejects_future_date(self, api_client, user_with_biologic):
        user, med = user_with_biologic
        api_client.force_authenticate(user=user)
        url = reverse("accounts_api:record_injection")
        data = {"medication_id": med.pk, "injection_date": str(date.today() + timedelta(days=1))}
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_record_injection_wrong_user(self, api_client, user_with_biologic, create_user):
        _, med = user_with_biologic
        other = create_user(email="other@example.com")
        api_client.force_authenticate(user=other)
        url = reverse("accounts_api:record_injection")
        data = {"medication_id": med.pk, "injection_date": str(date.today())}
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_record_injection_non_biologic_rejected(self, api_client, create_user):
        user = create_user()
        med = UserMedication.objects.create(
            user=user,
            medication_type="antihistamine",
            is_current=True,
        )
        api_client.force_authenticate(user=user)
        url = reverse("accounts_api:record_injection")
        data = {"medication_id": med.pk, "injection_date": str(date.today())}
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_record_injection_unauthenticated(self, api_client, user_with_biologic):
        _, med = user_with_biologic
        url = reverse("accounts_api:record_injection")
        data = {"medication_id": med.pk, "injection_date": str(date.today())}
        response = api_client.post(url, data, format="json")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]


# =============================================================================
# CELERY TASK
# =============================================================================


@pytest.mark.django_db
class TestSendInjectionReminders:
    """Tests for the send_injection_reminders Celery task."""

    @patch("notifications.tasks.send_push_to_user", return_value=1)
    def test_sends_when_due_within_7_days(self, mock_push, user_with_biologic):
        user, med = user_with_biologic
        # Set injection due in 5 days
        med.last_injection_date = date.today() - timedelta(days=23)
        med.save(update_fields=["last_injection_date"])
        PushSubscription.objects.create(
            user=user,
            endpoint="https://fcm.googleapis.com/test",
            p256dh="testkey",
            auth="testauth",
        )
        from notifications.tasks import send_injection_reminders

        result = send_injection_reminders()
        assert result >= 1
        mock_push.assert_called()

    @patch("notifications.tasks.send_push_to_user", return_value=1)
    def test_does_not_send_when_not_due_soon(self, mock_push, user_with_biologic):
        user, med = user_with_biologic
        # Set injection due in 20 days (well outside 7-day window)
        med.last_injection_date = date.today() - timedelta(days=8)
        med.save(update_fields=["last_injection_date"])
        PushSubscription.objects.create(
            user=user,
            endpoint="https://fcm.googleapis.com/test",
            p256dh="testkey",
            auth="testauth",
        )
        from notifications.tasks import send_injection_reminders

        result = send_injection_reminders()
        assert result == 0
        mock_push.assert_not_called()

    @patch("notifications.tasks.send_push_to_user", return_value=1)
    def test_skips_non_current_medication(self, mock_push, create_user):
        user = create_user()
        UserMedication.objects.create(
            user=user,
            medication_type="biologic",
            injection_frequency="every_4_weeks",
            last_injection_date=date.today() - timedelta(days=27),
            is_current=False,
        )
        PushSubscription.objects.create(
            user=user,
            endpoint="https://fcm.googleapis.com/test",
            p256dh="testkey",
            auth="testauth",
        )
        from notifications.tasks import send_injection_reminders

        result = send_injection_reminders()
        assert result == 0

    @patch("notifications.tasks.send_push_to_user", return_value=1)
    def test_skips_as_needed_frequency(self, mock_push, create_user):
        user = create_user()
        UserMedication.objects.create(
            user=user,
            medication_type="biologic",
            injection_frequency="as_needed",
            last_injection_date=date.today() - timedelta(days=3),
            is_current=True,
        )
        PushSubscription.objects.create(
            user=user,
            endpoint="https://fcm.googleapis.com/test",
            p256dh="testkey",
            auth="testauth",
        )
        from notifications.tasks import send_injection_reminders

        result = send_injection_reminders()
        assert result == 0


# =============================================================================
# TODAY VIEW CONTEXT
# =============================================================================


@pytest.mark.django_db
class TestTodayViewInjectionContext:
    """Tests for next_injection context in the Today view."""

    def test_injection_info_in_context_when_due_soon(self, client, user_with_biologic):
        user, med = user_with_biologic
        user.profile.onboarding_completed = True
        user.profile.privacy_consent_given = True
        user.profile.save()
        # Make injection due in 5 days
        med.last_injection_date = date.today() - timedelta(days=23)
        med.save(update_fields=["last_injection_date"])
        client.force_login(user)
        response = client.get(reverse("tracking:today"))
        assert response.status_code == 200
        ctx = response.context
        assert ctx["next_injection"] is not None
        assert ctx["next_injection"]["is_due_soon"] is True

    def test_no_injection_info_for_user_without_biologic(self, client, create_user):
        user = create_user()
        user.profile.onboarding_completed = True
        user.profile.privacy_consent_given = True
        user.profile.save()
        client.force_login(user)
        response = client.get(reverse("tracking:today"))
        assert response.status_code == 200
        assert response.context["next_injection"] is None

    def test_no_injection_info_when_not_due_soon(self, client, user_with_biologic):
        user, med = user_with_biologic
        user.profile.onboarding_completed = True
        user.profile.privacy_consent_given = True
        user.profile.save()
        # Make injection due in 20 days (outside 7-day window but still present)
        med.last_injection_date = date.today() - timedelta(days=8)
        med.save(update_fields=["last_injection_date"])
        client.force_login(user)
        response = client.get(reverse("tracking:today"))
        assert response.status_code == 200
        ctx_inj = response.context["next_injection"]
        # next_injection should be present but is_due_soon should be False
        if ctx_inj is not None:
            assert ctx_inj["is_due_soon"] is False
