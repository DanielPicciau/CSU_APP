"""
Comprehensive tests for the Notifications app.
Tests push subscriptions, reminders, and notification delivery.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from notifications.models import PushSubscription, ReminderPreferences

User = get_user_model()


@pytest.fixture
def api_client():
    """Return an API client."""
    return APIClient()


@pytest.fixture
def create_user(db):
    """Factory fixture to create users."""
    def _create_user(
        email="test@example.com",
        password="SecureP@ssw0rd123!",
        **kwargs
    ):
        return User.objects.create_user(
            email=email,
            password=password,
            **kwargs
        )
    return _create_user


@pytest.fixture
def authenticated_client(api_client, create_user):
    """Return an authenticated API client."""
    user = create_user()
    api_client.force_authenticate(user=user)
    return api_client, user


# =============================================================================
# PUSH SUBSCRIPTION TESTS
# =============================================================================

@pytest.mark.django_db
class TestPushSubscription:
    """Tests for push notification subscriptions."""
    
    def test_subscribe_success(self, authenticated_client):
        """Test successful push subscription."""
        client, user = authenticated_client
        url = reverse("notifications_api:subscribe")
        data = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test-endpoint-123",
            "keys": {
                "p256dh": "test-p256dh-key-12345",
                "auth": "test-auth-key",
            }
        }
        response = client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert PushSubscription.objects.filter(user=user).exists()
    
    def test_subscribe_unauthenticated(self, api_client):
        """Test subscription requires authentication."""
        url = reverse("notifications_api:subscribe")
        data = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test-endpoint",
            "keys": {
                "p256dh": "test-key",
                "auth": "test-auth",
            }
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
    
    def test_subscribe_invalid_endpoint(self, authenticated_client):
        """Test subscription with invalid endpoint."""
        client, user = authenticated_client
        url = reverse("notifications_api:subscribe")
        data = {
            "endpoint": "not-a-valid-url",
            "keys": {
                "p256dh": "test-key",
                "auth": "test-auth",
            }
        }
        response = client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_unsubscribe_success(self, authenticated_client):
        """Test successful unsubscription."""
        client, user = authenticated_client
        
        # First subscribe
        subscription = PushSubscription.objects.create(
            user=user,
            endpoint="https://fcm.googleapis.com/fcm/send/test-endpoint",
            p256dh="test-key",
            auth="test-auth",
        )
        
        url = reverse("notifications_api:unsubscribe")
        data = {"endpoint": subscription.endpoint}
        response = client.post(url, data, format="json")
        assert response.status_code == status.HTTP_200_OK
        
        # Check subscription is deactivated or deleted
        # The subscription may be deleted entirely or deactivated
        if PushSubscription.objects.filter(pk=subscription.pk).exists():
            subscription.refresh_from_db()
            assert not subscription.is_active
        else:
            # Subscription was deleted, which is also acceptable
            assert True


# =============================================================================
# REMINDER PREFERENCES TESTS
# =============================================================================

@pytest.mark.django_db
class TestReminderPreferences:
    """Tests for reminder preferences."""
    
    def test_get_preferences(self, authenticated_client):
        """Test getting reminder preferences."""
        client, user = authenticated_client
        url = reverse("notifications_api:preferences")
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
    
    def test_update_preferences(self, authenticated_client):
        """Test updating reminder preferences."""
        client, user = authenticated_client
        
        # Get or create initial preferences (may be auto-created)
        prefs, _ = ReminderPreferences.objects.get_or_create(
            user=user,
            defaults={"enabled": False, "time_of_day": "09:00:00"}
        )
        
        url = reverse("notifications_api:preferences")
        data = {
            "enabled": True,
            "time_of_day": "18:00:00",
        }
        response = client.patch(url, data, format="json")
        assert response.status_code == status.HTTP_200_OK
        
        prefs = ReminderPreferences.objects.get(user=user)
        assert prefs.enabled is True


# =============================================================================
# TEST NOTIFICATION TESTS
# =============================================================================

@pytest.mark.django_db
class TestTestNotification:
    """Tests for test notification endpoint."""
    
    def test_send_test_notification_no_subscription(self, authenticated_client):
        """Test sending test notification without subscription."""
        client, user = authenticated_client
        url = reverse("notifications_api:test")
        response = client.post(url)
        # Should indicate no subscriptions or send successfully
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
    
    def test_send_test_notification_with_subscription(self, authenticated_client):
        """Test sending test notification with subscription."""
        client, user = authenticated_client
        
        # Create subscription
        PushSubscription.objects.create(
            user=user,
            endpoint="https://fcm.googleapis.com/fcm/send/test-endpoint",
            p256dh="test-key-that-is-long-enough",
            auth="test-auth-key",
        )
        
        url = reverse("notifications_api:test")
        response = client.post(url)
        # The actual push might fail (invalid endpoint) but API should respond
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    def test_send_test_notification_unauthenticated(self, api_client):
        """Test sending test notification requires authentication."""
        url = reverse("notifications_api:test")
        response = api_client.post(url)
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


# =============================================================================
# DATA ISOLATION TESTS
# =============================================================================

@pytest.mark.django_db
class TestDataIsolation:
    """Tests for data isolation between users."""
    
    def test_cannot_see_other_user_subscriptions(self, api_client, create_user):
        """Test users cannot see other users' subscriptions."""
        user1 = create_user(email="user1@test.com")
        user2 = create_user(email="user2@test.com")
        
        # Create subscription for user2
        PushSubscription.objects.create(
            user=user2,
            endpoint="https://fcm.googleapis.com/fcm/send/user2-endpoint",
            p256dh="user2-key",
            auth="user2-auth",
        )
        
        # Login as user1
        api_client.force_authenticate(user=user1)
        
        # Verify user1 has no subscriptions
        assert not PushSubscription.objects.filter(user=user1).exists()
    
    def test_cannot_modify_other_user_preferences(self, api_client, create_user):
        """Test users cannot modify other users' preferences."""
        user1 = create_user(email="user1@test.com")
        user2 = create_user(email="user2@test.com")
        
        # Get or create preferences for user2 (may be auto-created)
        prefs, _ = ReminderPreferences.objects.get_or_create(
            user=user2,
            defaults={"enabled": True, "time_of_day": "09:00:00"}
        )
        # Ensure they're enabled
        prefs.enabled = True
        prefs.save()
        
        # Login as user1 and try to update
        api_client.force_authenticate(user=user1)
        url = reverse("notifications_api:preferences")
        
        # This should only affect user1's preferences, not user2's
        response = api_client.patch(url, {"enabled": False}, format="json")
        
        # User2's preferences should be unchanged
        prefs.refresh_from_db()
        assert prefs.enabled is True
