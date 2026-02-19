"""
API views for the tracking app.
"""

from datetime import date, timedelta

from django.db.models import Avg, Count
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DailyEntry
from .serializers import (
    DailyEntrySerializer,
    DailyEntryCreateUpdateSerializer,
    AdherenceMetricsSerializer,
    WeeklyStatsSerializer,
)
from .utils import apply_history_limit, get_aligned_week_bounds, get_history_limit_days, get_user_today


class DailyEntryListCreateView(generics.ListCreateAPIView):
    """List entries or create a new one."""

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DailyEntryCreateUpdateSerializer
        return DailyEntrySerializer

    def get_queryset(self):
        today = get_user_today(self.request.user)
        queryset = DailyEntry.objects.filter(user=self.request.user)
        
        # Filter by date range
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        queryset = apply_history_limit(queryset, self.request.user, today=today)
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
        today = get_user_today(self.request.user)
        return apply_history_limit(
            DailyEntry.objects.filter(user=self.request.user),
            self.request.user,
            today=today,
        )


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
        try:
            days = max(1, min(365, int(request.query_params.get("days", 7))))
        except (ValueError, TypeError):
            days = 7
        limit_days = get_history_limit_days(request.user)
        if limit_days is not None:
            days = min(days, limit_days)
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
        try:
            weeks = max(1, min(52, int(request.query_params.get("weeks", 4))))
        except (ValueError, TypeError):
            weeks = 4
        limit_days = get_history_limit_days(request.user)
        if limit_days is not None:
            max_weeks = max(1, limit_days // 7)
            weeks = min(weeks, max_weeks)
        today = get_user_today(request.user)
        
        # Compute all week bounds first, then fetch entries in a single query.
        week_bounds = [
            get_aligned_week_bounds(request.user, today, wn) for wn in range(weeks)
        ]
        overall_start = min(ws for ws, _ in week_bounds)
        overall_end = max(we for _, we in week_bounds)

        all_entries = {
            e["date"]: e["score"]
            for e in DailyEntry.objects.filter(
                user=request.user,
                date__gte=overall_start,
                date__lte=overall_end,
            ).values("date", "score")
        }

        results = []
        for w_start, w_end in week_bounds:
            uas7 = 0
            entries_count = 0
            for day_offset in range(7):
                day = w_start + timedelta(days=day_offset)
                if day in all_entries:
                    uas7 += all_entries[day]
                    entries_count += 1

            results.append({
                "week_start": w_start,
                "week_end": w_end,
                "uas7_score": uas7,
                "entries_count": entries_count,
                "complete": entries_count == 7,
            })
        
        serializer = WeeklyStatsSerializer(results, many=True)
        return Response(serializer.data)
