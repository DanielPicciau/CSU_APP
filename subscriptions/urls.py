"""
URL routes for subscriptions app.
"""

from django.urls import path

from . import views

app_name = "subscriptions"

urlpatterns = [
    # Premium landing page
    path("premium/", views.premium_landing_view, name="premium"),
    
    # Checkout flow
    path("checkout/", views.create_checkout_session, name="checkout"),
    path("success/", views.checkout_success_view, name="success"),
    path("canceled/", views.checkout_canceled_view, name="canceled"),
    
    # Subscription management
    path("cancel/", views.cancel_subscription_view, name="cancel"),
    path("reactivate/", views.reactivate_subscription_view, name="reactivate"),
    path("billing/", views.manage_billing_view, name="billing"),
    
    # Stripe webhook
    path("webhook/", views.stripe_webhook_view, name="webhook"),
]
