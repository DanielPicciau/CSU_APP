"""
Comprehensive tests for the Accounts app.
Tests authentication, authorization, and user management.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

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
# REGISTRATION TESTS
# =============================================================================

@pytest.mark.django_db
class TestRegistration:
    """Tests for user registration."""
    
    def test_register_success(self, api_client):
        """Test successful user registration."""
        url = reverse("accounts_api:register")
        data = {
            "email": "newuser@example.com",
            "password": "SecureP@ssw0rd123!",
            "password_confirm": "SecureP@ssw0rd123!",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(email="newuser@example.com").exists()
    
    def test_register_password_mismatch(self, api_client):
        """Test registration fails with mismatched passwords."""
        url = reverse("accounts_api:register")
        data = {
            "email": "newuser@example.com",
            "password": "SecureP@ssw0rd123!",
            "password_confirm": "DifferentPassword1!",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_register_weak_password(self, api_client):
        """Test registration fails with weak password."""
        url = reverse("accounts_api:register")
        data = {
            "email": "newuser@example.com",
            "password": "password",
            "password_confirm": "password",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_register_duplicate_email(self, api_client, create_user):
        """Test registration fails with duplicate email."""
        create_user(email="existing@example.com")
        url = reverse("accounts_api:register")
        data = {
            "email": "existing@example.com",
            "password": "SecureP@ssw0rd123!",
            "password_confirm": "SecureP@ssw0rd123!",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# AUTHENTICATION TESTS
# =============================================================================

@pytest.mark.django_db
class TestAuthentication:
    """Tests for user authentication."""
    
    def test_login_success(self, api_client, create_user):
        """Test successful login."""
        user = create_user()
        url = reverse("token_obtain_pair")
        data = {
            "email": user.email,
            "password": "SecureP@ssw0rd123!",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data
    
    def test_login_wrong_password(self, api_client, create_user):
        """Test login fails with wrong password."""
        user = create_user()
        url = reverse("token_obtain_pair")
        data = {
            "email": user.email,
            "password": "wrongpassword",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_nonexistent_user(self, api_client):
        """Test login fails for nonexistent user."""
        url = reverse("token_obtain_pair")
        data = {
            "email": "nonexistent@example.com",
            "password": "anypassword",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_token_refresh(self, api_client, create_user):
        """Test token refresh."""
        user = create_user()
        # First, get tokens
        url = reverse("token_obtain_pair")
        data = {"email": user.email, "password": "SecureP@ssw0rd123!"}
        response = api_client.post(url, data, format="json")
        refresh_token = response.data["refresh"]
        
        # Now refresh
        url = reverse("token_refresh")
        response = api_client.post(url, {"refresh": refresh_token}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data


# =============================================================================
# AUTHORIZATION TESTS
# =============================================================================

@pytest.mark.django_db
class TestAuthorization:
    """Tests for authorization and access control."""
    
    def test_unauthenticated_access_denied(self, api_client):
        """Test unauthenticated requests are denied."""
        url = reverse("accounts_api:me")
        response = api_client.get(url)
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
    
    def test_authenticated_access_allowed(self, authenticated_client):
        """Test authenticated requests are allowed."""
        client, user = authenticated_client
        url = reverse("accounts_api:me")
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
    
    def test_user_cannot_access_other_user_data(self, api_client, create_user):
        """Test users cannot access other users' data."""
        user1 = create_user(email="user1@test.com")
        user2 = create_user(email="user2@test.com")
        
        api_client.force_authenticate(user=user1)
        # This should only return user1's data, not user2's
        url = reverse("accounts_api:me")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == user1.email


# =============================================================================
# USER PROFILE TESTS
# =============================================================================

@pytest.mark.django_db
class TestUserProfile:
    """Tests for user profile management."""
    
    def test_get_profile(self, authenticated_client):
        """Test getting user profile."""
        client, user = authenticated_client
        url = reverse("accounts_api:me")
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == user.email
    
    def test_update_profile(self, authenticated_client):
        """Test updating user profile."""
        client, user = authenticated_client
        url = reverse("accounts_api:me")
        response = client.patch(url, {"first_name": "Updated"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.first_name == "Updated"


# =============================================================================
# PASSWORD TESTS
# =============================================================================

@pytest.mark.django_db
class TestPasswordManagement:
    """Tests for password management."""
    
    def test_change_password_success(self, authenticated_client):
        """Test successful password change."""
        client, user = authenticated_client
        url = reverse("accounts_api:password_change")
        data = {
            "old_password": "SecureP@ssw0rd123!",
            "new_password": "NewSecureP@ss456!",
            "new_password_confirm": "NewSecureP@ss456!",
        }
        response = client.post(url, data, format="json")
        assert response.status_code == status.HTTP_200_OK
    
    def test_change_password_wrong_old_password(self, authenticated_client):
        """Test password change fails with wrong old password."""
        client, user = authenticated_client
        url = reverse("accounts_api:password_change")
        data = {
            "old_password": "wrongpassword",
            "new_password": "NewSecureP@ss456!",
            "new_password_confirm": "NewSecureP@ss456!",
        }
        response = client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# INPUT VALIDATION TESTS
# =============================================================================

@pytest.mark.django_db
class TestInputValidation:
    """Tests for input validation and sanitization."""
    
    def test_long_input_rejected(self, api_client):
        """Test excessively long input is rejected."""
        url = reverse("accounts_api:register")
        data = {
            "email": "a" * 500 + "@example.com",  # Very long email
            "password": "SecureP@ssw0rd123!",
            "password_confirm": "SecureP@ssw0rd123!",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_email_validation(self, api_client):
        """Test email format validation."""
        url = reverse("accounts_api:register")
        data = {
            "email": "notanemail",
            "password": "SecureP@ssw0rd123!",
            "password_confirm": "SecureP@ssw0rd123!",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
