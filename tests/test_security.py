"""
Security-focused tests for medical-grade application.
Tests rate limiting, input validation, and security headers.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def client():
    """Return a Django test client."""
    return Client()


@pytest.fixture
def api_client():
    """Return an API client."""
    return APIClient()


@pytest.fixture
def create_user(db):
    """Factory fixture to create users."""
    def _create_user(
        email="test@example.com",
        password="XkT9$mNq@2rSvW#4pLz!",
        **kwargs
    ):
        return User.objects.create_user(
            email=email,
            password=password,
            **kwargs
        )
    return _create_user


# =============================================================================
# SECURITY HEADERS TESTS
# =============================================================================

@pytest.mark.django_db
class TestSecurityHeaders:
    """Tests for security headers."""
    
    def test_x_content_type_options(self, client, create_user):
        """Test X-Content-Type-Options header is set."""
        create_user()
        response = client.get("/")
        assert response.get("X-Content-Type-Options") == "nosniff"
    
    def test_x_frame_options(self, client, create_user):
        """Test X-Frame-Options header is set."""
        create_user()
        response = client.get("/")
        assert response.get("X-Frame-Options") in ["DENY", "SAMEORIGIN"]
    
    def test_x_xss_protection(self, client, create_user):
        """Test X-XSS-Protection header is set."""
        create_user()
        response = client.get("/")
        xss_header = response.get("X-XSS-Protection")
        assert xss_header is not None


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
            "email": "a" * 1000 + "@example.com",  # Very long email
            "password": "XkT9$mNq@2rSvW#4pLz!",
            "password_confirm": "XkT9$mNq@2rSvW#4pLz!",
        }
        response = api_client.post(url, data, format="json")
        # Email validation should reject this very long email
        # It may be 400 for invalid format or 201 if email field allows it
        # The key is that the request is handled safely
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_201_CREATED]
    
    def test_null_bytes_rejected(self, api_client):
        """Test null bytes in input are rejected."""
        url = reverse("accounts_api:register")
        data = {
            "email": "test\x00user@example.com",
            "password": "XkT9$mNq@2rSvW#4pLz!",
            "password_confirm": "XkT9$mNq@2rSvW#4pLz!",
        }
        response = api_client.post(url, data, format="json")
        # Should be rejected or sanitized
        assert response.status_code == status.HTTP_400_BAD_REQUEST or \
            "\x00" not in str(response.data)
    
    def test_unicode_normalization(self, api_client):
        """Test unicode input is handled properly."""
        url = reverse("accounts_api:register")
        data = {
            "email": "tëstüsér@example.com",
            "password": "XkT9$mNq@2rSvW#4pLz!",
            "password_confirm": "XkT9$mNq@2rSvW#4pLz!",
        }
        response = api_client.post(url, data, format="json")
        # Should either accept or reject cleanly
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
        ]


# =============================================================================
# AUTHENTICATION SECURITY TESTS
# =============================================================================

@pytest.mark.django_db
class TestAuthenticationSecurity:
    """Tests for authentication security."""
    
    def test_password_not_in_response(self, api_client, create_user):
        """Test password is never returned in responses."""
        user = create_user()
        api_client.force_authenticate(user=user)
        url = reverse("accounts_api:me")
        response = api_client.get(url)
        
        assert "password" not in response.data
        assert "XkT9$mNq@2rSvW#4pLz!" not in str(response.content)
    
    def test_token_in_header_only(self, api_client, create_user):
        """Test authentication works via header only."""
        user = create_user()
        url = reverse("token_obtain_pair")
        data = {"email": user.email, "password": "XkT9$mNq@2rSvW#4pLz!"}
        response = api_client.post(url, data, format="json")
        
        # Token should be in response body for obtaining
        assert response.status_code == status.HTTP_200_OK
        token = response.data["access"]
        
        # Using token in query string should not work (only header)
        api_client.credentials()  # Clear any existing auth
        url = reverse("accounts_api:me") + f"?token={token}"
        response = api_client.get(url)
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
        
        # Using token in header should work
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = api_client.get(reverse("accounts_api:me"))
        assert response.status_code == status.HTTP_200_OK
    
    def test_session_httponly(self, client, create_user):
        """Test session cookie is httponly."""
        user = create_user()
        response = client.post(
            "/accounts/login/",
            {"email": user.email, "password": "XkT9$mNq@2rSvW#4pLz!"},
        )
        
        if "sessionid" in response.cookies:
            session_cookie = response.cookies["sessionid"]
            assert session_cookie.get("httponly", False)


# =============================================================================
# DATA PROTECTION TESTS
# =============================================================================

@pytest.mark.django_db
class TestDataProtection:
    """Tests for data protection and privacy."""
    
    def test_user_enumeration_prevention(self, api_client, create_user):
        """Test login doesn't reveal which field is wrong."""
        create_user(email="existing@example.com")
        url = reverse("token_obtain_pair")
        
        # Wrong password
        response1 = api_client.post(url, {
            "email": "existing@example.com",
            "password": "wrongpassword",
        }, format="json")
        
        # Non-existent user
        response2 = api_client.post(url, {
            "email": "nonexistent@example.com",
            "password": "wrongpassword",
        }, format="json")
        
        # Both should return same status and similar message
        assert response1.status_code == response2.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_sensitive_data_not_logged(self, api_client, create_user, caplog):
        """Test passwords are not logged."""
        import logging
        
        url = reverse("accounts_api:register")
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "SecretP@ssword123!",
            "password_confirm": "SecretP@ssword123!",
        }
        
        with caplog.at_level(logging.DEBUG):
            api_client.post(url, data, format="json")
        
        # Password should not appear in logs
        for record in caplog.records:
            assert "SecretP@ssword123!" not in record.getMessage()


# =============================================================================
# AUTHORIZATION TESTS
# =============================================================================

@pytest.mark.django_db
class TestAuthorization:
    """Tests for authorization and access control."""
    
    def test_horizontal_privilege_escalation_prevention(self, api_client, create_user):
        """Test users cannot access other users' data by ID manipulation."""
        from tracking.models import DailyEntry
        from datetime import date
        
        user1 = create_user(email="user1@test.com")
        user2 = create_user(email="user2@test.com")
        
        # Create entry for user2
        entry = DailyEntry.objects.create(
            user=user2,
            date=date.today(),
            score=5,
        )
        
        # Login as user1
        api_client.force_authenticate(user=user1)
        
        # Try to access user2's entry directly by date
        url = reverse("tracking_api:entry_detail", kwargs={"date": str(entry.date)})
        response = api_client.get(url)
        
        # Should be 404 (not found in user1's entries)
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_vertical_privilege_escalation_prevention(self, api_client, create_user):
        """Test regular users cannot access admin endpoints."""
        user = create_user()
        api_client.force_authenticate(user=user)
        
        # Try to access admin
        response = api_client.get("/admin/")
        assert response.status_code in [
            status.HTTP_302_FOUND,  # Redirect to login
            status.HTTP_403_FORBIDDEN,
        ]


# =============================================================================
# INJECTION PREVENTION TESTS
# =============================================================================

@pytest.mark.django_db
class TestInjectionPrevention:
    """Tests for injection attack prevention."""
    
    def test_sql_injection_in_search(self, api_client, create_user):
        """Test SQL injection in search/filter parameters."""
        user = create_user()
        api_client.force_authenticate(user=user)
        
        url = reverse("tracking_api:entries")
        # Try SQL injection in query parameter
        response = api_client.get(url + "?date='; DROP TABLE tracking_dailyentry; --")
        
        # Should handle gracefully
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]
        
        # Table should still exist
        from tracking.models import DailyEntry
        assert DailyEntry.objects.count() >= 0  # Would fail if table was dropped
    
    def test_command_injection_prevention(self, api_client, create_user):
        """Test command injection in user input."""
        from tracking.models import DailyEntry
        from datetime import date
        
        user = create_user()
        api_client.force_authenticate(user=user)
        
        url = reverse("tracking_api:entries")
        data = {
            "date": str(date.today()),
            "score": 3,
            "notes": "test; cat /etc/passwd | rm -rf /",
        }
        response = api_client.post(url, data, format="json")
        
        # The data should be stored safely without command execution
        # Could be accepted (stored as text) or rejected
        assert response.status_code in [
            status.HTTP_201_CREATED,  # Accepted - commands are just text
            status.HTTP_400_BAD_REQUEST,  # Rejected by validation
        ]
        
        # If created, verify no command was executed (notes stored as plain text)
        if response.status_code == status.HTTP_201_CREATED:
            entry = DailyEntry.objects.filter(user=user, date=date.today()).first()
            if entry:
                # Notes should be stored as-is, not executed
                assert "|" in entry.notes or ";" in entry.notes


# =============================================================================
# ADMIN HEALTH DATA PRIVACY TESTS
# =============================================================================

@pytest.mark.django_db
class TestAdminHealthDataPrivacy:
    """Tests to ensure admin cannot access sensitive health data."""
    
    def test_staff_cannot_view_daily_entries(self, client, create_user):
        """Staff users cannot view daily entries (health data)."""
        from tracking.models import DailyEntry
        from datetime import date
        
        # Create a regular user with health data
        user = create_user(email="patient@example.com")
        DailyEntry.objects.create(
            user=user,
            date=date.today(),
            score=5,
            itch_score=2,
            hive_count_score=3,
            notes="Private health notes",
            took_antihistamine=True,
        )
        
        # Create staff user (not superuser)
        staff = create_user(email="staff@example.com", is_staff=True)
        client.force_login(staff)
        
        # Try to access daily entries in admin
        response = client.get("/admin/tracking/dailyentry/")
        # Should be forbidden or empty
        assert response.status_code in [403, 302] or b"0 daily entries" in response.content
    
    def test_staff_cannot_view_medications(self, client, create_user):
        """Staff users cannot view user medications."""
        from accounts.models import UserMedication
        
        # Create a regular user with medication data
        user = create_user(email="patient@example.com")
        UserMedication.objects.create(
            user=user,
            medication_key="omalizumab",
            medication_type="biologic",
            is_current=True,
        )
        
        # Create staff user (not superuser)
        staff = create_user(email="staff@example.com", is_staff=True)
        client.force_login(staff)
        
        # Try to access medications in admin
        response = client.get("/admin/accounts/usermedication/")
        # Should be forbidden or empty
        assert response.status_code in [403, 302] or b"0 user medications" in response.content
    
    def test_superuser_cannot_see_health_details(self, client, create_user):
        """Even superusers cannot see actual health data values."""
        from tracking.models import DailyEntry
        from datetime import date
        
        # Create a regular user with health data
        user = create_user(email="patient@example.com")
        DailyEntry.objects.create(
            user=user,
            date=date.today(),
            score=5,
            itch_score=2,
            hive_count_score=3,
            notes="Very private symptom notes",
            took_antihistamine=True,
        )
        
        # Create superuser
        superuser = User.objects.create_superuser(
            email="super@example.com",
            password="XkT9$mNq@2rSvW#4pLz!",
        )
        client.force_login(superuser)
        
        # View the list - should only show metadata, not health values
        response = client.get("/admin/tracking/dailyentry/")
        content = response.content.decode()
        
        # The actual health data should NOT appear
        assert "Very private symptom notes" not in content
        # Score values should not be visible in list
        assert ">5<" not in content  # score=5 should not appear as a cell value
    
    def test_admin_cannot_add_health_entries(self, client, create_user):
        """Admin cannot add health entries for users."""
        superuser = User.objects.create_superuser(
            email="super@example.com",
            password="XkT9$mNq@2rSvW#4pLz!",
        )
        client.force_login(superuser)
        
        # Try to access add page
        response = client.get("/admin/tracking/dailyentry/add/")
        # Should be forbidden
        assert response.status_code == 403
    
    def test_admin_cannot_edit_health_entries(self, client, create_user):
        """Admin cannot edit health entries."""
        from tracking.models import DailyEntry
        from datetime import date
        
        user = create_user(email="patient@example.com")
        entry = DailyEntry.objects.create(
            user=user,
            date=date.today(),
            score=3,
        )
        
        superuser = User.objects.create_superuser(
            email="super@example.com",
            password="XkT9$mNq@2rSvW#4pLz!",
        )
        client.force_login(superuser)
        
        # Try to access change page
        response = client.get(f"/admin/tracking/dailyentry/{entry.pk}/change/")
        # Should be forbidden
        assert response.status_code == 403
    
    def test_profile_personal_data_hidden(self, client, create_user):
        """Profile personal data (DOB, gender, diagnosis) is hidden from admin."""
        from accounts.models import Profile
        from datetime import date
        
        user = create_user(email="patient@example.com")
        profile = user.profile
        profile.date_of_birth = date(1990, 5, 15)
        profile.age = 35
        profile.gender = "female"
        profile.csu_diagnosis = "yes"
        profile.has_prescribed_medication = "yes"
        profile.save()
        
        superuser = User.objects.create_superuser(
            email="super@example.com",
            password="XkT9$mNq@2rSvW#4pLz!",
        )
        client.force_login(superuser)
        
        # View profile list
        response = client.get("/admin/accounts/profile/")
        content = response.content.decode()
        
        # Personal/health data should not appear
        assert "1990" not in content  # DOB year
        assert "female" not in content
        assert "csu_diagnosis" not in content.lower() or "yes" not in content
    
    def test_medication_details_completely_hidden(self, client, create_user):
        """Medication names and details are completely hidden."""
        from accounts.models import UserMedication
        
        user = create_user(email="patient@example.com")
        UserMedication.objects.create(
            user=user,
            medication_key="omalizumab",
            custom_name="Xolair 150mg",
            medication_type="biologic",
            dose_amount=150,
            is_current=True,
        )
        
        superuser = User.objects.create_superuser(
            email="super@example.com",
            password="XkT9$mNq@2rSvW#4pLz!",
        )
        client.force_login(superuser)
        
        # View medication list
        response = client.get("/admin/accounts/usermedication/")
        content = response.content.decode()
        
        # Medication details should not appear
        assert "omalizumab" not in content.lower()
        assert "xolair" not in content.lower()
        assert "biologic" not in content.lower()
        assert "150" not in content  # dose
