"""
API views for the accounts app.
"""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.security import audit_logger, rate_limit
from subscriptions.entitlements import has_entitlement, resolve_entitlements
from subscriptions.models import Subscription
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
            
            # Invalidate all other sessions using the shared helper
            from .views import _invalidate_user_sessions
            current_key = (
                request.session.session_key
                if hasattr(request, "session") and request.session.session_key
                else None
            )
            sessions_invalidated = _invalidate_user_sessions(user, current_key)
            
            if current_key:
                # Update current session to stay logged in
                update_session_auth_hash(request, user)
                request.session.cycle_key()
            
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


class EntitlementsAPIView(APIView):
    """Return current user's entitlements and subscription summary."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        entitlements = resolve_entitlements(request.user)
        subscription = Subscription.objects.select_related("plan").filter(
            user=request.user
        ).first()
        plan = subscription.plan if subscription else None

        history_limit_days = None
        if not has_entitlement(request.user, "history_unlimited"):
            history_limit_days = getattr(settings, "FREE_HISTORY_DAYS", 30)

        data = {
            "entitlements": entitlements,
            "is_premium": entitlements.get("premium_access", False),
            "history_limit_days": history_limit_days,
            "subscription": {
                "normalized_status": subscription.normalized_status if subscription else "free",
                "provider_status": subscription.status if subscription else None,
                "current_period_end": (
                    subscription.current_period_end.isoformat()
                    if subscription and subscription.current_period_end
                    else None
                ),
                "cancel_at_period_end": (
                    subscription.cancel_at_period_end if subscription else False
                ),
                "plan": (
                    {
                        "id": plan.id,
                        "name": plan.name,
                        "price_gbp": str(plan.price_gbp),
                        "billing_period": plan.billing_period,
                    }
                    if plan
                    else None
                ),
            },
        }

        return Response(data, status=status.HTTP_200_OK)
