"""
API views for the notifications app.
"""

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PushSubscription, ReminderPreferences
from .serializers import (
    PushSubscriptionSerializer,
    PushSubscriptionCreateSerializer,
    ReminderPreferencesSerializer,
)
from .tasks import send_test_notification


class PushSubscriptionCreateView(APIView):
    """Register a new push subscription."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Create or update a push subscription."""
        serializer = PushSubscriptionCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        if serializer.is_valid():
            subscription = serializer.save()
            return Response(
                PushSubscriptionSerializer(subscription).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PushSubscriptionDeleteView(APIView):
    """Unsubscribe from push notifications."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Delete subscription by endpoint."""
        endpoint = request.data.get("endpoint")
        if not endpoint:
            return Response(
                {"error": "endpoint is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        deleted, _ = PushSubscription.objects.filter(
            user=request.user,
            endpoint=endpoint,
        ).delete()
        
        if deleted:
            return Response({"status": "unsubscribed"})
        return Response(
            {"error": "subscription not found"},
            status=status.HTTP_404_NOT_FOUND,
        )


class ReminderPreferencesView(generics.RetrieveUpdateAPIView):
    """Get or update reminder preferences."""

    serializer_class = ReminderPreferencesSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        preferences, _ = ReminderPreferences.objects.get_or_create(
            user=self.request.user
        )
        return preferences


class TestNotificationView(APIView):
    """Send a test push notification."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Trigger test notification - always runs synchronously."""
        # Always run synchronously (PythonAnywhere free tier has no Redis)
        try:
            result = send_test_notification(request.user.id)
            return Response({"status": "sent", "result": result})
        except Exception as e:
            import traceback
            return Response({
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
