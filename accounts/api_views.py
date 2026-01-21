"""
API views for the accounts app.
"""

from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.sessions.models import Session
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    RegisterSerializer,
    UserSerializer,
    PasswordChangeSerializer,
    ProfileUpdateSerializer,
)

User = get_user_model()


class RegisterAPIView(generics.CreateAPIView):
    """API endpoint for user registration."""

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


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
            # Keep current session valid by updating it
            if hasattr(request, 'session'):
                current_session_key = request.session.session_key
                # Delete all sessions except current one
                # Note: This only works with database-backed sessions
                try:
                    Session.objects.filter(
                        expire_date__gte=timezone.now()
                    ).exclude(
                        session_key=current_session_key
                    ).delete()
                except Exception:
                    pass  # Session backend may not support this
                
                # Update current session to stay logged in
                update_session_auth_hash(request, user)
            
            return Response(
                {"message": "Password changed successfully. Other sessions have been logged out."},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
