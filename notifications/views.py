"""
Views for the notifications app (Django templates).
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect

from .forms import ReminderPreferencesForm
from .models import ReminderPreferences, PushSubscription


@login_required
def reminder_settings_view(request):
    """View and update reminder preferences."""
    # Get or create preferences
    preferences, created = ReminderPreferences.objects.get_or_create(user=request.user)
    
    # Get active subscriptions count
    subscriptions_count = PushSubscription.objects.filter(
        user=request.user,
        is_active=True,
    ).count()
    
    if request.method == "POST":
        form = ReminderPreferencesForm(request.POST, instance=preferences)
        if form.is_valid():
            form.save()
            messages.success(request, "Reminder settings updated!")
            return redirect("notifications:settings")
    else:
        form = ReminderPreferencesForm(instance=preferences)
    
    return render(request, "notifications/settings_new.html", {
        "form": form,
        "preferences": preferences,
        "subscriptions_count": subscriptions_count,
    })


@login_required
def subscriptions_list_view(request):
    """List user's push subscriptions."""
    subscriptions = PushSubscription.objects.filter(
        user=request.user,
    ).order_by("-created_at")
    
    return render(request, "notifications/subscriptions.html", {
        "subscriptions": subscriptions,
    })


@login_required
def delete_subscription_view(request, subscription_id):
    """Delete a push subscription."""
    if request.method == "POST":
        try:
            subscription = PushSubscription.objects.get(
                pk=subscription_id,
                user=request.user,
            )
            subscription.delete()
            messages.success(request, "Subscription removed.")
        except PushSubscription.DoesNotExist:
            messages.error(request, "Subscription not found.")
    
    return redirect("notifications:subscriptions")


@login_required
def test_notification_view(request):
    """Send a test notification."""
    from .tasks import send_test_notification
    
    if request.method == "POST":
        # Send test notification async
        send_test_notification.delay(request.user.id)
        return JsonResponse({"status": "sent"})
    
    return JsonResponse({"error": "POST required"}, status=405)
