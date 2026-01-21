"""
API views for the tracking app.
"""

from datetime import date, timedelta

from django.db.models import Avg, Count
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

import pytz

from .models import DailyEntry
from .serializers import (
    DailyEntrySerializer,
    DailyEntryCreateUpdateSerializer,
    AdherenceMetricsSerializer,
    WeeklyStatsSerializer,
)


def get_user_today(user) -> date:
    """Get today's date in the user's timezone."""
    from django.utils import timezone
    user_tz = pytz.timezone(user.profile.default_timezone)
    return timezone.now().astimezone(user_tz).date()


class DailyEntryListCreateView(generics.ListCreateAPIView):
    """List entries or create a new one."""

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DailyEntryCreateUpdateSerializer
        return DailyEntrySerializer

    def get_queryset(self):
        queryset = DailyEntry.objects.filter(user=self.request.user)
        
        # Filter by date range
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        return queryset.order_by("-date")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class DailyEntryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a specific entry."""

    serializer_class = DailyEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "date"
    lookup_url_kwarg = "date"

    def get_queryset(self):
        return DailyEntry.objects.filter(user=self.request.user)


class TodayEntryView(APIView):
    """Get or create/update today's entry."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get today's entry."""
        today = get_user_today(request.user)
        entry = DailyEntry.objects.filter(user=request.user, date=today).first()
        
        if entry:
            serializer = DailyEntrySerializer(entry)
            return Response(serializer.data)
        
        return Response(
            {"date": today, "has_entry": False},
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        """Create or update today's entry (upsert)."""
        today = get_user_today(request.user)
        entry = DailyEntry.objects.filter(user=request.user, date=today).first()
        
        data = request.data.copy()
        data["date"] = today
        
        if entry:
            serializer = DailyEntryCreateUpdateSerializer(entry, data=data, partial=True)
        else:
            serializer = DailyEntryCreateUpdateSerializer(data=data)
        
        if serializer.is_valid():
            serializer.save(user=request.user, date=today)
            return Response(
                DailyEntrySerializer(
                    DailyEntry.objects.get(user=request.user, date=today)
                ).data,
                status=status.HTTP_200_OK if entry else status.HTTP_201_CREATED,
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdherenceMetricsView(APIView):
    """Get adherence metrics for the user."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get adherence stats for specified period."""
        days = int(request.query_params.get("days", 7))
        today = get_user_today(request.user)
        start_date = today - timedelta(days=days - 1)
        
        entries = DailyEntry.objects.filter(
            user=request.user,
            date__gte=start_date,
            date__lte=today,
        )
        
        entries_count = entries.count()
        avg_score = entries.aggregate(avg=Avg("score"))["avg"]
        
        # Find missing dates
        entry_dates = set(entries.values_list("date", flat=True))
        all_dates = {start_date + timedelta(days=i) for i in range(days)}
        missing_dates = sorted(all_dates - entry_dates)
        
        data = {
            "period_days": days,
            "entries_count": entries_count,
            "adherence_percentage": (entries_count / days) * 100,
            "average_score": round(avg_score, 2) if avg_score else None,
            "missing_dates": missing_dates,
        }
        
        serializer = AdherenceMetricsSerializer(data)
        return Response(serializer.data)


class WeeklyStatsView(APIView):
    """Get weekly UAS7 statistics."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get UAS7 scores for recent weeks."""
        weeks = int(request.query_params.get("weeks", 4))
        today = get_user_today(request.user)
        
        results = []
        for week_num in range(weeks):
            week_end = today - timedelta(days=week_num * 7)
            week_start = week_end - timedelta(days=6)
            
            entries = DailyEntry.objects.filter(
                user=request.user,
                date__gte=week_start,
                date__lte=week_end,
            )
            
            entries_count = entries.count()
            uas7 = sum(e.score for e in entries)
            
            results.append({
                "week_start": week_start,
                "week_end": week_end,
                "uas7_score": uas7,
                "entries_count": entries_count,
                "complete": entries_count == 7,
            })
        
        serializer = WeeklyStatsSerializer(results, many=True)
        return Response(serializer.data)
