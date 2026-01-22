"""
API views for the accounts app.
"""

import logging

from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.sessions.models import Session
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.security import audit_logger, rate_limit
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    PasswordChangeSerializer,
    ProfileUpdateSerializer,
)

logger = logging.getLogger('security')
User = get_user_model()


class RegisterAPIView(generics.CreateAPIView):
    """
    API endpoint for user registration.
    
    SECURITY: This is a public endpoint with strict rate limiting.
    - Validates password against medical-grade policy
    - Logs registration attempts for security monitoring
    - Does not reveal if email already exists (timing-safe)
    """

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    # Note: Additional rate limiting is applied via middleware (3/minute)
    
    def create(self, request, *args, **kwargs):
        # Log registration attempt (don't log email to avoid PII in logs)
        from core.security import audit_logger, get_client_ip
        audit_logger.log_action(
            'REGISTRATION_ATTEMPT',
            None,
            request,
            details={'ip': get_client_ip(request)}
        )
        return super().create(request, *args, **kwargs)


class UserDetailAPIView(generics.RetrieveUpdateAPIView):
    """API endpoint for retrieving and updating the current user."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ProfileUpdateAPIView(generics.UpdateAPIView):
    """API endpoint for updating user profile."""

    serializer_class = ProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.profile


class PasswordChangeAPIView(APIView):
    """API endpoint for changing password."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={"request": request},
        )
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data["new_password"])
            user.save()
            
            # Invalidate all other sessions for this user (security best practice)
            sessions_invalidated = 0
            if hasattr(request, 'session') and request.session.session_key:
                current_session_key = request.session.session_key
                # Delete all sessions for this user except current one
                # We need to decode sessions to find those belonging to this user
                try:
                    from django.contrib.sessions.backends.db import SessionStore
                    all_sessions = Session.objects.filter(expire_date__gte=timezone.now())
                    for session in all_sessions:
                        if session.session_key == current_session_key:
                            continue
                        try:
                            session_data = session.get_decoded()
                            if session_data.get('_auth_user_id') == str(user.pk):
                                session.delete()
                                sessions_invalidated += 1
                        except Exception:
                            continue
                except Exception as e:
                    logger.warning(f"Failed to invalidate other sessions: {e}")
                
                # Update current session to stay logged in
                update_session_auth_hash(request, user)
            
            # Audit log the password change
            audit_logger.log_action(
                'PASSWORD_CHANGE',
                user,
                request,
                details={'sessions_invalidated': sessions_invalidated}
            )
            
            return Response(
                {"message": "Password changed successfully. Other sessions have been logged out."},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
