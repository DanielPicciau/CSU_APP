"""
Pytest fixtures for CSU Tracker tests.
"""

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

User = get_user_model()


def pytest_configure():
    """Configure pytest settings."""
    settings.TESTING = True
    # Disable rate limiting in tests
    settings.RATELIMIT_ENABLE = False


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear Django cache before and after each test to prevent cache pollution."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    """Return an API client for testing."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create and return a test user."""
    return User.objects.create_user(
        email="testuser@example.com",
        password="SecurePass123!@#",
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """Return an authenticated API client."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def other_user(db):
    """Create and return another test user."""
    return User.objects.create_user(
        email="otheruser@example.com",
        password="SecurePass123!@#",
    )


@pytest.fixture
def superuser(db):
    """Create and return a superuser."""
    return User.objects.create_superuser(
        email="admin@example.com",
        password="AdminPass123!@#",
    )
