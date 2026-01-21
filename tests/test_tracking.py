"""
Comprehensive tests for the Tracking app.
Tests CSU score logging, history, and data integrity.
"""

import pytest
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from tracking.models import DailyEntry

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
# ENTRY CREATION TESTS
# =============================================================================

@pytest.mark.django_db
class TestEntryCreation:
    """Tests for creating CSU entries."""
    
    def test_create_entry_success(self, authenticated_client):
        """Test successful entry creation."""
        client, user = authenticated_client
        url = reverse("tracking_api:entries")
        data = {
            "date": str(date.today()),
            "score": 3,
        }
        response = client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert DailyEntry.objects.filter(user=user).exists()
    
    def test_create_entry_unauthenticated(self, api_client):
        """Test entry creation requires authentication."""
        url = reverse("tracking_api:entries")
        data = {
            "date": str(date.today()),
            "score": 3,
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
    
    def test_create_entry_invalid_score(self, authenticated_client):
        """Test validation of score values."""
        client, user = authenticated_client
        url = reverse("tracking_api:entries")
        
        # Score too high
        data = {
            "date": str(date.today()),
            "score": 100,  # Invalid - max is 42
        }
        response = client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Negative score
        data = {
            "date": str(date.today()),
            "score": -1,
        }
        response = client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# ENTRY RETRIEVAL TESTS
# =============================================================================

@pytest.mark.django_db
class TestEntryRetrieval:
    """Tests for retrieving entries."""
    
    def test_list_own_entries(self, authenticated_client):
        """Test user can list their own entries."""
        client, user = authenticated_client
        DailyEntry.objects.create(user=user, date=date.today() - timedelta(days=1), score=3)
        DailyEntry.objects.create(user=user, date=date.today() - timedelta(days=2), score=4)
        
        url = reverse("tracking_api:entries")
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        # Check we got results (could be paginated or not)
        data = response.data
        if isinstance(data, dict) and "results" in data:
            assert len(data["results"]) == 2
        else:
            assert len(data) == 2
    
    def test_cannot_see_other_users_entries(self, api_client, create_user):
        """Test user cannot see other users' entries."""
        user1 = create_user(email="user1@test.com")
        user2 = create_user(email="user2@test.com")
        
        # Create entries for user2
        DailyEntry.objects.create(user=user2, date=date.today(), score=5)
        
        # Login as user1
        api_client.force_authenticate(user=user1)
        url = reverse("tracking_api:entries")
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        # User1 should see 0 entries (not user2's)
        data = response.data
        if isinstance(data, dict) and "results" in data:
            assert len(data["results"]) == 0
        else:
            assert len(data) == 0


# =============================================================================
# ENTRY UPDATE/DELETE TESTS
# =============================================================================

@pytest.mark.django_db
class TestEntryModification:
    """Tests for modifying entries."""
    
    def test_update_own_entry(self, authenticated_client):
        """Test user can update their own entry."""
        client, user = authenticated_client
        entry = DailyEntry.objects.create(user=user, date=date.today(), score=3)
        
        url = reverse("tracking_api:entry_detail", kwargs={"date": str(entry.date)})
        response = client.patch(url, {"score": 4}, format="json")
        assert response.status_code == status.HTTP_200_OK
        entry.refresh_from_db()
        assert entry.score == 4
    
    def test_cannot_update_other_user_entry(self, api_client, create_user):
        """Test user cannot update another user's entry."""
        user1 = create_user(email="user1@test.com")
        user2 = create_user(email="user2@test.com")
        
        entry = DailyEntry.objects.create(user=user2, date=date.today(), score=3)
        
        api_client.force_authenticate(user=user1)
        url = reverse("tracking_api:entry_detail", kwargs={"date": str(entry.date)})
        response = api_client.patch(url, {"score": 4}, format="json")
        # Should be 404 (not found in user1's entries)
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_delete_own_entry(self, authenticated_client):
        """Test user can delete their own entry."""
        client, user = authenticated_client
        entry = DailyEntry.objects.create(user=user, date=date.today(), score=3)
        
        url = reverse("tracking_api:entry_detail", kwargs={"date": str(entry.date)})
        response = client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not DailyEntry.objects.filter(pk=entry.pk).exists()


# =============================================================================
# STATISTICS TESTS
# =============================================================================

@pytest.mark.django_db
class TestStatistics:
    """Tests for statistics endpoints."""
    
    def test_weekly_stats(self, authenticated_client):
        """Test weekly stats endpoint."""
        client, user = authenticated_client
        
        # Create entries for the past week
        for i in range(7):
            DailyEntry.objects.create(
                user=user,
                date=date.today() - timedelta(days=i),
                score=i,
            )
        
        url = reverse("tracking_api:weekly")
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
    
    def test_today_entry(self, authenticated_client):
        """Test today endpoint."""
        client, user = authenticated_client
        
        url = reverse("tracking_api:today")
        response = client.get(url)
        # Should work even if no entry exists
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
