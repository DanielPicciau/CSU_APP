"""
Views for Cura Premium subscription management.
"""

import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

import stripe

from audit.utils import log_event
from .entitlements import invalidate_entitlements_cache
from .models import Subscription, SubscriptionPlan, SubscriptionStatus, user_is_premium
from core.security import hash_sensitive_data


logger = logging.getLogger(__name__)


def get_stripe_configured() -> bool:
    """Check if Stripe is properly configured."""
    return bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_PRICE_ID)


def init_stripe():
    """Initialize Stripe with secret key."""
    if not settings.STRIPE_SECRET_KEY:
        raise ValueError("STRIPE_SECRET_KEY is not configured")
    stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
def premium_landing_view(request):
    """
    Landing page for Cura Premium subscription.
    
    Shows subscription status and upgrade options.
    """
    is_premium = user_is_premium(request.user)
    subscription = None
    
    try:
        subscription = request.user.subscription
    except Subscription.DoesNotExist:
        pass
    
    context = {
        "is_premium": is_premium,
        "subscription": subscription,
        "stripe_configured": get_stripe_configured(),
        "stripe_public_key": settings.STRIPE_PUBLISHABLE_KEY,
        "monthly_price": "2.99",
        "currency": "GBP",
    }
    
    return render(request, "subscriptions/premium.html", context)


@login_required
@require_POST
def create_checkout_session(request):
    """
    Create a Stripe Checkout session for subscription.
    """
    if not get_stripe_configured():
        messages.error(request, "Subscription service is not available at this time.")
        return redirect("subscriptions:premium")
    
    try:
        init_stripe()
        
        # Get or create Stripe customer
        subscription, created = Subscription.objects.get_or_create(user=request.user)

        if not subscription.plan:
            subscription.plan = SubscriptionPlan.get_default_plan()
            subscription.save(update_fields=["plan"])
        
        if not subscription.stripe_customer_id:
            # Create new Stripe customer
            customer = stripe.Customer.create(
                email=request.user.email,
                metadata={"user_id": str(request.user.id)},
            )
            subscription.stripe_customer_id = customer.id
            subscription.save()
        
        # Build success and cancel URLs
        success_url = request.build_absolute_uri("/subscriptions/success/")
        cancel_url = request.build_absolute_uri("/subscriptions/canceled/")
        
        # Create Checkout Session
        checkout_session = stripe.checkout.Session.create(
            customer=subscription.stripe_customer_id,
            payment_method_types=["card"],
            line_items=[
                {
                    "price": settings.STRIPE_PRICE_ID,
                    "quantity": 1,
                },
            ],
            mode="subscription",
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            metadata={
                "user_id": str(request.user.id),
            },
        )
        
        return redirect(checkout_session.url)
    
    except stripe.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {e}")
        messages.error(request, "Unable to start checkout. Please try again later.")
        return redirect("subscriptions:premium")
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        messages.error(request, "An error occurred. Please try again later.")
        return redirect("subscriptions:premium")


@login_required
def checkout_success_view(request):
    """
    Success page after successful checkout.
    """
    session_id = request.GET.get("session_id")
    
    if session_id and get_stripe_configured():
        try:
            init_stripe()
            session = stripe.checkout.Session.retrieve(session_id)
            
            # Update subscription record
            subscription_id = session.subscription
            if subscription_id:
                stripe_sub = stripe.Subscription.retrieve(subscription_id)
                update_subscription_from_stripe(request.user, stripe_sub)
        except Exception as e:
            logger.error(f"Error processing checkout success: {e}")
    
    return render(request, "subscriptions/success.html", {
        "is_premium": user_is_premium(request.user),
    })


@login_required
def checkout_canceled_view(request):
    """
    Page shown when user cancels checkout.
    """
    return render(request, "subscriptions/canceled.html")


@login_required
@require_POST
def cancel_subscription_view(request):
    """
    Cancel the user's subscription at period end.
    """
    if not get_stripe_configured():
        messages.error(request, "Subscription service is not available.")
        return redirect("subscriptions:premium")
    
    try:
        subscription = request.user.subscription
        
        if not subscription.stripe_subscription_id:
            messages.error(request, "No active subscription found.")
            return redirect("subscriptions:premium")
        
        init_stripe()
        
        # Cancel at period end (user keeps access until then)
        stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=True,
        )
        
        subscription.cancel_at_period_end = True
        subscription.save()

        log_event(
            action="subscription_cancel_scheduled",
            target_type="subscription",
            target_id=subscription.id,
            actor=request.user,
            metadata={
                "current_period_end": (
                    subscription.current_period_end.isoformat()
                    if subscription.current_period_end
                    else None
                ),
            },
        )
        
        messages.success(
            request,
            "Your subscription will be canceled at the end of the current billing period. "
            "You'll continue to have access until then."
        )
        
    except Subscription.DoesNotExist:
        messages.error(request, "No subscription found.")
    except stripe.StripeError as e:
        logger.error(f"Stripe error canceling subscription: {e}")
        messages.error(request, "Unable to cancel subscription. Please try again.")
    except Exception as e:
        logger.error(f"Error canceling subscription: {e}")
        messages.error(request, "An error occurred. Please try again.")
    
    return redirect("subscriptions:premium")


@login_required
@require_POST
def reactivate_subscription_view(request):
    """
    Reactivate a subscription that was set to cancel at period end.
    """
    if not get_stripe_configured():
        messages.error(request, "Subscription service is not available.")
        return redirect("subscriptions:premium")
    
    try:
        subscription = request.user.subscription
        
        if not subscription.stripe_subscription_id:
            messages.error(request, "No subscription found.")
            return redirect("subscriptions:premium")
        
        init_stripe()
        
        # Remove cancel_at_period_end flag
        stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=False,
        )
        
        subscription.cancel_at_period_end = False
        subscription.save()

        log_event(
            action="subscription_reactivated",
            target_type="subscription",
            target_id=subscription.id,
            actor=request.user,
        )
        
        messages.success(request, "Your subscription has been reactivated!")
        
    except Subscription.DoesNotExist:
        messages.error(request, "No subscription found.")
    except stripe.StripeError as e:
        logger.error(f"Stripe error reactivating subscription: {e}")
        messages.error(request, "Unable to reactivate subscription. Please try again.")
    except Exception as e:
        logger.error(f"Error reactivating subscription: {e}")
        messages.error(request, "An error occurred. Please try again.")
    
    return redirect("subscriptions:premium")


@login_required
def manage_billing_view(request):
    """
    Redirect to Stripe Customer Portal for billing management.
    """
    if not get_stripe_configured():
        messages.error(request, "Billing management is not available.")
        return redirect("subscriptions:premium")
    
    try:
        subscription = request.user.subscription
        
        if not subscription.stripe_customer_id:
            messages.error(request, "No billing account found.")
            return redirect("subscriptions:premium")
        
        init_stripe()
        
        return_url = request.build_absolute_uri("/subscriptions/premium/")
        
        portal_session = stripe.billing_portal.Session.create(
            customer=subscription.stripe_customer_id,
            return_url=return_url,
        )
        
        return redirect(portal_session.url)
    
    except Subscription.DoesNotExist:
        messages.error(request, "No subscription found.")
        return redirect("subscriptions:premium")
    except stripe.StripeError as e:
        logger.error(f"Stripe error creating portal session: {e}")
        messages.error(request, "Unable to access billing portal. Please try again.")
        return redirect("subscriptions:premium")


@csrf_exempt
@require_POST
def stripe_webhook_view(request):
    """
    Handle Stripe webhook events.
    
    Processes subscription updates, payment events, etc.
    """
    payload = request.body
    sig_header = request.headers.get("Stripe-Signature")
    
    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.warning("Stripe webhook received but STRIPE_WEBHOOK_SECRET not configured")
        return HttpResponse(status=400)
    
    try:
        init_stripe()
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid webhook payload: {e}")
        return HttpResponse(status=400)
    except stripe.SignatureVerificationError as e:
        logger.error(f"Invalid webhook signature: {e}")
        return HttpResponse(status=400)
    
    # Handle subscription events
    event_type = event["type"]
    data_object = event["data"]["object"]
    
    logger.info(f"Processing Stripe webhook: {event_type}")
    
    try:
        if event_type == "customer.subscription.created":
            handle_subscription_created(data_object)
        elif event_type == "customer.subscription.updated":
            handle_subscription_updated(data_object)
        elif event_type == "customer.subscription.deleted":
            handle_subscription_deleted(data_object)
        elif event_type == "invoice.payment_succeeded":
            handle_payment_succeeded(data_object)
        elif event_type == "invoice.payment_failed":
            handle_payment_failed(data_object)
    except Exception as e:
        logger.error(f"Error processing webhook {event_type}: {e}")
        # Still return 200 to acknowledge receipt
    
    return HttpResponse(status=200)


def update_subscription_from_stripe(user, stripe_sub):
    """
    Update local subscription record from Stripe subscription object.
    """
    subscription, created = Subscription.objects.get_or_create(user=user)
    previous_status = subscription.status
    previous_cancel = subscription.cancel_at_period_end

    if not subscription.plan:
        subscription.plan = SubscriptionPlan.get_default_plan()
    
    subscription.stripe_subscription_id = stripe_sub.id
    subscription.stripe_customer_id = stripe_sub.customer
    subscription.status = stripe_sub.status
    subscription.cancel_at_period_end = stripe_sub.cancel_at_period_end
    
    # Update price ID from first item
    if stripe_sub.get("items") and stripe_sub["items"].get("data"):
        subscription.stripe_price_id = stripe_sub["items"]["data"][0]["price"]["id"]
    
    # Convert timestamps
    if stripe_sub.get("current_period_start"):
        subscription.current_period_start = datetime.fromtimestamp(
            stripe_sub["current_period_start"]
        )
    if stripe_sub.get("current_period_end"):
        subscription.current_period_end = datetime.fromtimestamp(
            stripe_sub["current_period_end"]
        )
    if stripe_sub.get("canceled_at"):
        subscription.canceled_at = datetime.fromtimestamp(stripe_sub["canceled_at"])
    if stripe_sub.get("trial_end"):
        subscription.trial_end = datetime.fromtimestamp(stripe_sub["trial_end"])

    if stripe_sub.status == SubscriptionStatus.PAST_DUE:
        grace_days = getattr(settings, "SUBSCRIPTION_GRACE_DAYS", 7)
        if not subscription.grace_period_end or subscription.grace_period_end < timezone.now():
            subscription.grace_period_end = timezone.now() + timedelta(days=grace_days)
    else:
        subscription.grace_period_end = None
    
    subscription.save()
    invalidate_entitlements_cache(user.id)

    if previous_status != subscription.status or previous_cancel != subscription.cancel_at_period_end:
        log_event(
            action="subscription_updated",
            target_type="subscription",
            target_id=subscription.id,
            actor=user,
            metadata={
                "from_status": previous_status,
                "to_status": subscription.status,
                "cancel_at_period_end": subscription.cancel_at_period_end,
            },
        )
    return subscription


def handle_subscription_created(stripe_sub):
    """Handle new subscription creation."""
    customer_id = stripe_sub["customer"]
    
    try:
        subscription = Subscription.objects.get(stripe_customer_id=customer_id)
        update_subscription_from_stripe(subscription.user, stripe_sub)
        logger.info(
            "Subscription created for user_id=%s user_hash=%s",
            subscription.user.id,
            hash_sensitive_data(subscription.user.email),
        )
    except Subscription.DoesNotExist:
        logger.warning(f"No local subscription found for customer {customer_id}")


def handle_subscription_updated(stripe_sub):
    """Handle subscription updates."""
    subscription_id = stripe_sub["id"]
    
    try:
        subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
        update_subscription_from_stripe(subscription.user, stripe_sub)
        logger.info(
            "Subscription updated for user_id=%s user_hash=%s",
            subscription.user.id,
            hash_sensitive_data(subscription.user.email),
        )
    except Subscription.DoesNotExist:
        # Try by customer ID
        customer_id = stripe_sub["customer"]
        try:
            subscription = Subscription.objects.get(stripe_customer_id=customer_id)
            update_subscription_from_stripe(subscription.user, stripe_sub)
            logger.info(
                "Subscription updated for user_id=%s user_hash=%s",
                subscription.user.id,
                hash_sensitive_data(subscription.user.email),
            )
        except Subscription.DoesNotExist:
            logger.warning(f"No local subscription found for {subscription_id}")


def handle_subscription_deleted(stripe_sub):
    """Handle subscription cancellation/deletion."""
    subscription_id = stripe_sub["id"]
    
    try:
        subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
        subscription.status = SubscriptionStatus.CANCELED
        subscription.canceled_at = datetime.now()
        subscription.grace_period_end = None
        subscription.save()
        log_event(
            action="subscription_canceled",
            target_type="subscription",
            target_id=subscription.id,
            actor=None,
            metadata={"provider_subscription_id": subscription.stripe_subscription_id},
        )
        logger.info(
            "Subscription canceled for user_id=%s user_hash=%s",
            subscription.user.id,
            hash_sensitive_data(subscription.user.email),
        )
    except Subscription.DoesNotExist:
        logger.warning(f"No local subscription found for {subscription_id}")


def handle_payment_succeeded(invoice):
    """Handle successful payment."""
    subscription_id = invoice.get("subscription")
    if not subscription_id:
        return
    
    try:
        subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
        # Refresh subscription data from Stripe
        init_stripe()
        stripe_sub = stripe.Subscription.retrieve(subscription_id)
        update_subscription_from_stripe(subscription.user, stripe_sub)
        logger.info(
            "Payment succeeded for user_id=%s user_hash=%s",
            subscription.user.id,
            hash_sensitive_data(subscription.user.email),
        )
    except Subscription.DoesNotExist:
        logger.warning(f"No local subscription found for {subscription_id}")


def handle_payment_failed(invoice):
    """Handle failed payment."""
    subscription_id = invoice.get("subscription")
    if not subscription_id:
        return
    
    try:
        subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
        # Refresh subscription data from Stripe
        init_stripe()
        stripe_sub = stripe.Subscription.retrieve(subscription_id)
        update_subscription_from_stripe(subscription.user, stripe_sub)
        logger.warning(
            "Payment failed for user_id=%s user_hash=%s",
            subscription.user.id,
            hash_sensitive_data(subscription.user.email),
        )
    except Subscription.DoesNotExist:
        logger.warning(f"No local subscription found for {subscription_id}")
