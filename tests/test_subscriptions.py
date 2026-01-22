"""
Tests for Cura Premium subscription functionality.
"""

import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

from subscriptions.models import Subscription, SubscriptionStatus, user_is_premium


User = get_user_model()


@pytest.fixture
def user(db):
    """Create a test user with completed onboarding."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
    # Mark onboarding as completed to avoid redirect
    user.profile.onboarding_completed = True
    user.profile.save()
    return user


@pytest.fixture
def premium_user(db, user):
    """Create a user with an active premium subscription."""
    subscription = Subscription.objects.create(
        user=user,
        stripe_customer_id="cus_test123",
        stripe_subscription_id="sub_test123",
        status=SubscriptionStatus.ACTIVE,
    )
    return user


@pytest.fixture
def client_logged_in(client, user):
    """Return a client logged in as the test user."""
    client.login(email="test@example.com", password="testpass123")
    return client


@pytest.fixture
def premium_client_logged_in(client, premium_user):
    """Return a client logged in as a premium user."""
    client.login(email="test@example.com", password="testpass123")
    return client


class TestUserIsPremium:
    """Test the user_is_premium helper function."""
    
    def test_unauthenticated_user_not_premium(self, db):
        """Anonymous user should not be premium."""
        from django.contrib.auth.models import AnonymousUser
        assert user_is_premium(AnonymousUser()) is False
    
    def test_user_without_subscription_not_premium(self, user):
        """User without subscription should not be premium."""
        assert user_is_premium(user) is False
    
    def test_user_with_active_subscription_is_premium(self, premium_user):
        """User with active subscription should be premium."""
        assert user_is_premium(premium_user) is True
    
    def test_user_with_canceled_subscription_not_premium(self, user):
        """User with canceled subscription should not be premium."""
        Subscription.objects.create(
            user=user,
            status=SubscriptionStatus.CANCELED,
        )
        assert user_is_premium(user) is False
    
    def test_superuser_always_premium(self, db):
        """Superuser should always have premium access."""
        superuser = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123",
        )
        assert user_is_premium(superuser) is True
    
    def test_trialing_user_is_premium(self, user):
        """User with trialing subscription should have premium access."""
        Subscription.objects.create(
            user=user,
            status=SubscriptionStatus.TRIALING,
        )
        assert user_is_premium(user) is True


class TestSubscriptionModel:
    """Test Subscription model properties."""
    
    def test_is_premium_active(self, premium_user):
        """Active subscription should return is_premium=True."""
        assert premium_user.subscription.is_premium is True
    
    def test_is_premium_canceled(self, user):
        """Canceled subscription should return is_premium=False."""
        subscription = Subscription.objects.create(
            user=user,
            status=SubscriptionStatus.CANCELED,
        )
        assert subscription.is_premium is False
    
    def test_subscription_str(self, premium_user):
        """Test subscription string representation."""
        assert "test@example.com" in str(premium_user.subscription)
        assert "active" in str(premium_user.subscription).lower()


class TestPremiumLandingView:
    """Test the premium landing page."""
    
    def test_premium_page_requires_login(self, client):
        """Premium page should require authentication."""
        response = client.get(reverse("subscriptions:premium"))
        assert response.status_code == 302
        assert "login" in response.url
    
    def test_premium_page_shows_upgrade_for_free_user(self, client_logged_in):
        """Free user should see upgrade options."""
        response = client_logged_in.get(reverse("subscriptions:premium"))
        assert response.status_code == 200
        assert b"Cura Premium" in response.content
        assert b"2.99" in response.content
    
    def test_premium_page_shows_status_for_premium_user(self, premium_client_logged_in):
        """Premium user should see subscription status."""
        response = premium_client_logged_in.get(reverse("subscriptions:premium"))
        assert response.status_code == 200
        assert b"Your Subscription" in response.content


class TestExportPremiumGate:
    """Test that detailed export features are gated behind premium."""
    
    def test_export_page_accessible_to_all(self, client_logged_in):
        """Export page should be accessible (shows premium prompt for detailed)."""
        response = client_logged_in.get(reverse("tracking:export"))
        assert response.status_code == 200
    
    def test_quick_csv_export_allowed_for_free_user(self, client_logged_in):
        """Free user should be able to export quick summary CSV."""
        response = client_logged_in.get(reverse("tracking:export_csv") + "?report_type=quick")
        # Should not redirect to premium (may fail for other reasons like no data)
        assert "premium" not in response.get("Location", "")
    
    def test_quick_pdf_export_allowed_for_free_user(self, client_logged_in):
        """Free user should be able to export quick summary PDF."""
        response = client_logged_in.get(reverse("tracking:export_pdf") + "?report_type=quick")
        # Should not redirect to premium
        assert "premium" not in response.get("Location", "")
    
    def test_detailed_csv_export_blocked_for_free_user(self, client_logged_in):
        """Free user should be redirected when trying to export detailed CSV."""
        response = client_logged_in.get(reverse("tracking:export_csv") + "?report_type=detailed")
        assert response.status_code == 302
        assert "premium" in response.url
    
    def test_detailed_pdf_export_blocked_for_free_user(self, client_logged_in):
        """Free user should be redirected when trying to export detailed PDF."""
        response = client_logged_in.get(reverse("tracking:export_pdf") + "?report_type=detailed")
        assert response.status_code == 302
        assert "premium" in response.url
    
    def test_detailed_csv_export_allowed_for_premium_user(self, premium_client_logged_in):
        """Premium user should be able to download detailed CSV."""
        response = premium_client_logged_in.get(reverse("tracking:export_csv") + "?report_type=detailed")
        # Should not redirect to premium
        assert "premium" not in response.get("Location", "")
    
    def test_detailed_pdf_export_allowed_for_premium_user(self, premium_client_logged_in):
        """Premium user should be able to download detailed PDF."""
        response = premium_client_logged_in.get(reverse("tracking:export_pdf") + "?report_type=detailed")
        # Should not redirect to premium
        assert "premium" not in response.get("Location", "")


class TestCheckoutFlow:
    """Test the checkout flow views."""
    
    def test_checkout_requires_login(self, client):
        """Checkout should require authentication."""
        response = client.post(reverse("subscriptions:checkout"))
        assert response.status_code == 302
        assert "login" in response.url
    
    def test_success_page_requires_login(self, client):
        """Success page should require authentication."""
        response = client.get(reverse("subscriptions:success"))
        assert response.status_code == 302
        assert "login" in response.url
    
    def test_canceled_page_requires_login(self, client):
        """Canceled page should require authentication."""
        response = client.get(reverse("subscriptions:canceled"))
        assert response.status_code == 302
        assert "login" in response.url
    
    def test_success_page_accessible_when_logged_in(self, client_logged_in):
        """Success page should be accessible when logged in."""
        response = client_logged_in.get(reverse("subscriptions:success"))
        assert response.status_code == 200
        assert b"Welcome" in response.content or b"Premium" in response.content
    
    def test_canceled_page_accessible_when_logged_in(self, client_logged_in):
        """Canceled page should be accessible when logged in."""
        response = client_logged_in.get(reverse("subscriptions:canceled"))
        assert response.status_code == 200


class TestSubscriptionManagement:
    """Test subscription management views."""
    
    def test_cancel_requires_login(self, client):
        """Cancel should require authentication."""
        response = client.post(reverse("subscriptions:cancel"))
        assert response.status_code == 302
        assert "login" in response.url
    
    def test_reactivate_requires_login(self, client):
        """Reactivate should require authentication."""
        response = client.post(reverse("subscriptions:reactivate"))
        assert response.status_code == 302
        assert "login" in response.url
    
    def test_billing_requires_login(self, client):
        """Billing portal should require authentication."""
        response = client.get(reverse("subscriptions:billing"))
        assert response.status_code == 302
        assert "login" in response.url


class TestWebhook:
    """Test Stripe webhook handling."""
    
    def test_webhook_rejects_get_request(self, client):
        """Webhook should reject GET requests."""
        response = client.get(reverse("subscriptions:webhook"))
        assert response.status_code == 405
    
    def test_webhook_rejects_without_signature(self, client):
        """Webhook should reject requests without proper signature."""
        response = client.post(
            reverse("subscriptions:webhook"),
            data="{}",
            content_type="application/json",
        )
        # Should reject due to missing webhook secret or signature
        assert response.status_code == 400
