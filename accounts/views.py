"""
Views for the accounts app (Django templates).
"""

import logging

from django.contrib import messages
from django.http import HttpResponse
import secrets
from datetime import timedelta

import pyotp
from django.conf import settings
from django.contrib.auth import login, logout, update_session_auth_hash, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.sessions.models import Session
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes, force_str
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.utils import timezone

from core.security import AccountLockout, get_client_ip, audit_logger, rate_limit, hash_sensitive_data

from .forms import (
    CustomAuthenticationForm,
    RegisterForm,
    ProfileForm,
    CustomPasswordChangeForm,
    DeleteAccountForm,
    PasswordResetRequestForm,
    PasswordResetConfirmForm,
    MFASetupForm,
    MFAVerifyForm,
    OnboardingAccountForm,
    OnboardingNameForm,
    OnboardingAgeForm,
    OnboardingGenderForm,
    OnboardingDiagnosisForm,
    OnboardingMedicationStatusForm,
    OnboardingMedicationSelectForm,
    OnboardingAntihistamineDetailsForm,
    OnboardingInjectionDetailsForm,
    OnboardingPrivacyConsentForm,
    OnboardingReminderForm,
)

from .models import COMMON_MEDICATIONS, UserMedication, PasswordResetToken, UserMFA

User = get_user_model()
logger = logging.getLogger("security")


class CustomLoginView(LoginView):
    """Custom login view with styled form and security features."""

    template_name = "accounts/login.html"
    authentication_form = CustomAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("home")
    
    def get_lockout_identifier(self, request):
        """Get identifier for lockout tracking (IP + attempted email)."""
        ip = get_client_ip(request)
        email = request.POST.get('username', '')
        return f"{ip}:{email.lower()}"
    
    def dispatch(self, request, *args, **kwargs):
        """Check for account lockout before processing."""
        if request.method == 'POST':
            identifier = self.get_lockout_identifier(request)
            if AccountLockout.is_locked(identifier):
                remaining = AccountLockout.get_lockout_remaining(identifier)
                minutes = remaining // 60 + 1
                messages.error(
                    request,
                    f"Too many failed login attempts. Please try again in {minutes} minute(s)."
                )
                return redirect('accounts:login')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        """Reset lockout and log successful login."""
        identifier = self.get_lockout_identifier(self.request)
        AccountLockout.reset_attempts(identifier)
        # Audit log successful login
        user = form.get_user()
        audit_logger.log_login(user, self.request, success=True)

        # If MFA is enabled (or required for admins), defer login until verified
        mfa_required = user.is_staff or user.is_superuser
        has_mfa = hasattr(user, "mfa") and user.mfa.enabled
        if mfa_required or has_mfa:
            self.request.session["mfa_pending_user_id"] = str(user.pk)
            self.request.session["mfa_next"] = str(self.get_success_url())
            return redirect("accounts:mfa_verify")

        response = super().form_valid(form)
        # Rotate session key on login
        self.request.session.cycle_key()
        return response
    
    def form_invalid(self, form):
        """Track failed login attempt and log it."""
        identifier = self.get_lockout_identifier(self.request)
        attempts, is_locked = AccountLockout.record_failed_attempt(identifier)
        
        # Audit log failed login attempt
        audit_logger.log_action(
            'LOGIN_FAILED',
            None,
            self.request,
            details={
                'email_attempted_hash': (
                    hash_sensitive_data(self.request.POST.get('username', '').strip().lower())
                    if self.request.POST.get('username')
                    else None
                )
            },
            success=False
        )
        
        if is_locked:
            remaining = AccountLockout.get_lockout_remaining(identifier)
            minutes = remaining // 60 + 1
            messages.error(
                self.request,
                f"Too many failed login attempts. Account is locked for {minutes} minute(s)."
            )
        elif attempts >= 3:
            remaining_attempts = AccountLockout.MAX_FAILED_ATTEMPTS - attempts
            messages.warning(
                self.request,
                f"{remaining_attempts} login attempt(s) remaining before temporary lockout."
            )
        
        return super().form_invalid(form)


class CustomLogoutView(LogoutView):
    """Custom logout view with audit logging."""

    next_page = reverse_lazy("accounts:login")
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            audit_logger.log_logout(request.user, request)
        return super().dispatch(request, *args, **kwargs)


class RegisterView(CreateView):
    """User registration view - redirects to onboarding flow."""

    template_name = "accounts/register.html"
    form_class = RegisterForm
    success_url = reverse_lazy("home")

    def dispatch(self, request, *args, **kwargs):
        # Redirect to onboarding for new users
        if not request.user.is_authenticated:
            return redirect("accounts:onboarding_welcome")
        return redirect("home")


@login_required
def profile_view(request):
    """View and update user profile."""
    profile = request.user.profile
    
    # Get tracking stats for display
    from tracking.models import DailyEntry
    total_entries = DailyEntry.objects.filter(user=request.user).count()
    
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=profile)

    return render(request, "accounts/profile_new.html", {
        "form": form,
        "profile": profile,
        "total_entries": total_entries,
    })


@login_required
def change_password_view(request):
    """Change user password with rate limiting."""
    # Rate limit password changes to prevent brute force on current password
    from django.core.cache import cache
    user_id = request.user.id
    rate_key = f"password_change:{user_id}"
    attempts = cache.get(rate_key, 0)
    
    if attempts >= 5:  # Max 5 attempts per 15 minutes
        messages.error(request, "Too many password change attempts. Please try again later.")
        return redirect("accounts:profile")
    
    if request.method == "POST":
        cache.set(rate_key, attempts + 1, 900)  # 15 minutes
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Reset rate limit on success
            cache.delete(rate_key)
            # Keep user logged in after password change
            update_session_auth_hash(request, user)
            request.session.cycle_key()
            # Audit log the password change
            audit_logger.log_action('PASSWORD_CHANGE', user, request)
            messages.success(request, "Your password has been changed successfully!")
            return redirect("notifications:settings")
    else:
        form = CustomPasswordChangeForm(request.user)

    return render(request, "accounts/change_password.html", {
        "form": form,
    })


@login_required
def delete_account_view(request):
    """Delete user account with audit logging."""
    if request.method == "POST":
        form = DeleteAccountForm(request.user, request.POST)
        if form.is_valid():
            user = request.user
            # Audit log the deletion before it happens
            audit_logger.log_action('ACCOUNT_DELETION', user, request)
            logout(request)
            user.delete()
            messages.success(request, "Your account has been permanently deleted.")
            return redirect("accounts:login")
    else:
        form = DeleteAccountForm(request.user)

    return render(request, "accounts/delete_account.html", {
        "form": form,
    })


def _invalidate_user_sessions(user, current_session_key: str | None = None) -> int:
    """Invalidate all sessions for a user except the current session (optional)."""
    sessions_invalidated = 0
    try:
        all_sessions = Session.objects.filter(expire_date__gte=timezone.now())
        for session in all_sessions:
            if current_session_key and session.session_key == current_session_key:
                continue
            try:
                session_data = session.get_decoded()
                if session_data.get('_auth_user_id') == str(user.pk):
                    session.delete()
                    sessions_invalidated += 1
            except Exception:
                continue
    except Exception as exc:
        logger.warning(f"Failed to invalidate sessions: {exc}")
    return sessions_invalidated


@rate_limit("password_reset", 5, 900)
@require_http_methods(["GET", "POST"])
def password_reset_request_view(request):
    """Request a password reset link (never reveal if email exists)."""
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()

            # Always respond with a generic message
            messages.success(
                request,
                "If an account exists for that email, we've sent a reset link.",
            )

            user = User.objects.filter(email__iexact=email, is_active=True).first()
            if user:
                # Invalidate existing unused tokens
                PasswordResetToken.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())

                token = secrets.token_urlsafe(32)
                token_hash = PasswordResetToken.hash_token(token)
                ttl_minutes = getattr(settings, "PASSWORD_RESET_TOKEN_TTL_MINUTES", 30)
                expires_at = timezone.now() + timedelta(minutes=ttl_minutes)

                PasswordResetToken.objects.create(
                    user=user,
                    token_hash=token_hash,
                    expires_at=expires_at,
                    requested_ip=get_client_ip(request),
                    requested_user_agent=request.META.get("HTTP_USER_AGENT", "")[:200],
                )

                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                reset_url = request.build_absolute_uri(
                    reverse_lazy("accounts:password_reset_confirm", kwargs={"uidb64": uidb64, "token": token})
                )

                subject = "Reset your CSU Tracker password"
                message = (
                    "We received a request to reset your CSU Tracker password.\n\n"
                    f"Reset your password using this link (valid for {ttl_minutes} minutes):\n"
                    f"{reset_url}\n\n"
                    "If you did not request this, you can ignore this email."
                )
                try:
                    send_mail(
                        subject,
                        message,
                        getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@csutracker.local"),
                        [user.email],
                        fail_silently=True,
                    )
                    audit_logger.log_action("PASSWORD_RESET_REQUEST", user, request)
                except Exception as exc:
                    logger.warning(f"Failed to send password reset email: {exc}")

            return redirect("accounts:login")
    else:
        form = PasswordResetRequestForm()

    return render(request, "accounts/password_reset_request.html", {"form": form})


@rate_limit("password_reset_confirm", 10, 900)
@require_http_methods(["GET", "POST"])
def password_reset_confirm_view(request, uidb64: str, token: str):
    """Confirm password reset using a single-use, hashed token."""
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=user_id)
    except Exception:
        user = None

    if request.method == "POST":
        form = PasswordResetConfirmForm(request.POST)
        if form.is_valid():
            if not user:
                messages.error(request, "This reset link is invalid or has expired.")
                return redirect("accounts:password_reset_request")

            token_hash = PasswordResetToken.hash_token(token)
            reset_record = PasswordResetToken.objects.filter(
                user=user,
                token_hash=token_hash,
                used_at__isnull=True,
                expires_at__gte=timezone.now(),
            ).first()

            if not reset_record:
                messages.error(request, "This reset link is invalid or has expired.")
                return redirect("accounts:password_reset_request")

            user.set_password(form.cleaned_data["new_password1"])
            user.save()
            reset_record.mark_used()
            _invalidate_user_sessions(user)
            audit_logger.log_action("PASSWORD_RESET_CONFIRM", user, request)
            messages.success(request, "Your password has been reset. Please sign in.")
            return redirect("accounts:login")
    else:
        form = PasswordResetConfirmForm()

    return render(request, "accounts/password_reset_confirm.html", {"form": form})


@rate_limit("mfa_setup", 10, 600)
@require_http_methods(["GET", "POST"])
def mfa_setup_view(request):
    """Enable MFA for a logged-in user."""
    user = request.user if request.user.is_authenticated else None
    if not user:
        pending_user_id = request.session.get("mfa_pending_user_id")
        if not pending_user_id:
            return redirect("accounts:login")
        try:
            user = User.objects.get(pk=pending_user_id)
        except User.DoesNotExist:
            return redirect("accounts:login")
    mfa, _ = UserMFA.objects.get_or_create(user=user, defaults={"secret": pyotp.random_base32()})

    if request.method == "POST":
        form = MFASetupForm(request.POST)
        if form.is_valid():
            totp = pyotp.TOTP(mfa.secret)
            if totp.verify(form.cleaned_data["code"], valid_window=1):
                mfa.enabled = True
                mfa.confirmed_at = timezone.now()
                mfa.last_used_at = timezone.now()
                mfa.save(update_fields=["enabled", "confirmed_at", "last_used_at"])
                messages.success(request, "MFA enabled successfully.")
                if request.user.is_authenticated:
                    return redirect("accounts:profile")
                return redirect("accounts:mfa_verify")
            messages.error(request, "Invalid code. Please try again.")
    else:
        form = MFASetupForm()

    provisioning_uri = pyotp.TOTP(mfa.secret).provisioning_uri(
        name=user.email,
        issuer_name="CSU Tracker",
    )

    return render(request, "accounts/mfa_setup.html", {
        "form": form,
        "secret": mfa.secret,
        "provisioning_uri": provisioning_uri,
        "is_enabled": mfa.enabled,
    })


@rate_limit("mfa_verify", 10, 600)
@require_http_methods(["GET", "POST"])
def mfa_verify_view(request):
    """Verify MFA during login flow."""
    pending_user_id = request.session.get("mfa_pending_user_id")
    if not pending_user_id:
        return redirect("accounts:login")

    try:
        user = User.objects.get(pk=pending_user_id)
    except User.DoesNotExist:
        request.session.pop("mfa_pending_user_id", None)
        return redirect("accounts:login")

    mfa = getattr(user, "mfa", None)
    if not mfa or not mfa.enabled:
        # Require admins to set up MFA before login
        if user.is_staff or user.is_superuser:
            return redirect("accounts:mfa_setup")
        return redirect("accounts:login")

    if request.method == "POST":
        form = MFAVerifyForm(request.POST)
        if form.is_valid():
            totp = pyotp.TOTP(mfa.secret)
            if totp.verify(form.cleaned_data["code"], valid_window=1):
                login(request, user)
                request.session.cycle_key()
                request.session.pop("mfa_pending_user_id", None)
                next_url = request.session.pop("mfa_next", None)
                mfa.last_used_at = timezone.now()
                mfa.save(update_fields=["last_used_at"])
                return redirect(next_url or "home")
            messages.error(request, "Invalid code. Please try again.")
    else:
        form = MFAVerifyForm()

    return render(request, "accounts/mfa_verify.html", {"form": form})


@login_required
def privacy_view(request):
    """Privacy policy and data explanation."""
    profile = request.user.profile
    
    if request.method == "POST":
        # Handle privacy preference toggle
        allow_analytics = request.POST.get("allow_analytics") == "on"
        profile.allow_data_collection = allow_analytics
        profile.save()
        messages.success(request, "Privacy preferences updated.")
        return redirect("accounts:privacy")
    
    return render(request, "accounts/privacy.html", {
        "profile": profile,
    })


@login_required
@require_http_methods(["POST"])
def accept_consent_view(request):
    """Handle privacy consent acceptance."""
    profile = request.user.profile
    profile.privacy_consent_given = True
    profile.privacy_consent_date = timezone.now()
    profile.save(update_fields=['privacy_consent_given', 'privacy_consent_date'])
    
    return HttpResponse("")


# =============================================================================
# ONBOARDING VIEWS
# A calm, step-by-step guided experience for new users
# =============================================================================

ONBOARDING_STEPS = [
    {"name": "welcome", "title": "Welcome", "required": False},
    {"name": "account", "title": "Create Account", "required": True},
    {"name": "name", "title": "Your Name", "required": False},
    {"name": "age", "title": "Your Age", "required": False},
    {"name": "gender", "title": "Gender", "required": False},
    {"name": "diagnosis", "title": "CSU Status", "required": False},
    {"name": "medication_status", "title": "Treatment", "required": False},
    {"name": "medication_select", "title": "Medications", "required": False, "conditional": True},
    {"name": "medication_details", "title": "Details", "required": False, "conditional": True},
    {"name": "summary", "title": "Summary", "required": False},
    {"name": "privacy", "title": "Privacy", "required": True},
    {"name": "reminders", "title": "Reminders", "required": False},
    {"name": "complete", "title": "All Set", "required": False},
]

def get_onboarding_context(step_index, exclude_conditional=False):
    """Generate context for onboarding progress."""
    steps = ONBOARDING_STEPS
    if exclude_conditional:
        steps = [s for s in steps if not s.get("conditional")]
    total_steps = len(steps)
    return {
        "current_step": step_index + 1,
        "total_steps": total_steps,
        "progress_percent": int((step_index / (total_steps - 1)) * 100) if total_steps > 1 else 100,
        "step_info": ONBOARDING_STEPS[step_index] if step_index < len(ONBOARDING_STEPS) else None,
        "steps": steps,
    }


def onboarding_welcome(request):
    """Step 1: Welcome screen with app explanation."""
    # If user is already logged in and has completed onboarding, go to home
    if request.user.is_authenticated:
        if request.user.profile.onboarding_completed:
            return redirect("home")
    
    context = get_onboarding_context(0)
    return render(request, "accounts/onboarding/welcome.html", context)

from core.security import rate_limit


def onboarding_account(request):
    """Step 2: Account creation with personal details and rate limiting."""
    if request.user.is_authenticated:
        # Already logged in, skip to gender step (we now skip name/age since collected here)
        return redirect("accounts:onboarding_gender")
    
    # Rate limit account creation to prevent abuse
    from django.core.cache import cache
    ip = get_client_ip(request)
    rate_key = f"onboarding_account:{ip}"
    attempts = cache.get(rate_key, 0)
    
    if attempts >= 5:  # Max 5 attempts per 15 minutes
        messages.error(request, "Too many account creation attempts. Please try again later.")
        return redirect("accounts:onboarding_welcome")
    
    if request.method == "POST":
        # Increment rate limit counter
        cache.set(rate_key, attempts + 1, 900)  # 15 minutes
        
        form = OnboardingAccountForm(request.POST)
        if form.is_valid():
            # Create user with first/last name
            user = User.objects.create_user(
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
                first_name=form.cleaned_data["first_name"],
                last_name=form.cleaned_data["last_name"],
            )
            
            # Save DOB and calculate age to profile
            dob = form.cleaned_data["date_of_birth"]
            if dob:
                from datetime import date
                today = date.today()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                user.profile.age = age
                user.profile.date_of_birth = dob
            
            # Use first name as display name
            user.profile.display_name = form.cleaned_data["first_name"]
            user.profile.onboarding_step = 2
            user.profile.save()
            
            # Audit log the registration
            audit_logger.log_action('REGISTRATION', user, request)
            
            # Log them in immediately
            login(request, user)
            
            # Skip name and age steps, go directly to gender
            return redirect("accounts:onboarding_gender")
    else:
        form = OnboardingAccountForm()
    
    context = get_onboarding_context(1)
    context["form"] = form
    return render(request, "accounts/onboarding/account.html", context)



@login_required
def onboarding_gender(request):
    """Step 5: How do you describe your gender?"""
    profile = request.user.profile
    
    if request.method == "POST":
        action = request.POST.get("action", "next")
        
        if action == "skip":
            profile.onboarding_step = 5
            profile.save()
            return redirect("accounts:onboarding_diagnosis")
        
        if action == "back":
            return redirect("accounts:onboarding_welcome")
        
        form = OnboardingGenderForm(request.POST)
        if form.is_valid():
            profile.gender = form.cleaned_data.get("gender", "")
            profile.onboarding_step = 5
            profile.save()
            return redirect("accounts:onboarding_diagnosis")
    else:
        form = OnboardingGenderForm(initial={"gender": profile.gender})
    
    context = get_onboarding_context(4)
    context["form"] = form
    context["can_skip"] = True
    context["can_go_back"] = True
    context["gender_options"] = [
        {"value": "male", "label": "Male", "icon": "👨"},
        {"value": "female", "label": "Female", "icon": "👩"},
        {"value": "non_binary", "label": "Non-binary", "icon": "🧑"},
        {"value": "prefer_not_to_say", "label": "Prefer not to say", "icon": "🔒"},
    ]
    return render(request, "accounts/onboarding/gender.html", context)


@login_required
def onboarding_diagnosis(request):
    """Step 6: Have you been diagnosed with CSU?"""
    profile = request.user.profile
    
    if request.method == "POST":
        action = request.POST.get("action", "next")
        
        if action == "skip":
            profile.onboarding_step = 6
            profile.save()
            return redirect("accounts:onboarding_medication_status")
        
        if action == "back":
            return redirect("accounts:onboarding_gender")
        
        form = OnboardingDiagnosisForm(request.POST)
        if form.is_valid():
            profile.csu_diagnosis = form.cleaned_data.get("csu_diagnosis", "")
            profile.onboarding_step = 6
            profile.save()
            return redirect("accounts:onboarding_medication_status")
    else:
        form = OnboardingDiagnosisForm(initial={"csu_diagnosis": profile.csu_diagnosis})
    
    context = get_onboarding_context(5)
    context["form"] = form
    context["can_skip"] = True
    context["can_go_back"] = True
    context["diagnosis_options"] = [
        {"value": "yes", "label": "Yes", "description": "I have a formal diagnosis"},
        {"value": "no", "label": "No", "description": "I haven't been diagnosed"},
        {"value": "unsure", "label": "Unsure", "description": "I'm still figuring it out"},
    ]
    return render(request, "accounts/onboarding/diagnosis.html", context)


@login_required
def onboarding_medication_status(request):
    """Step 7: Have you been prescribed medication?"""
    profile = request.user.profile
    
    if request.method == "POST":
        action = request.POST.get("action", "next")
        
        if action == "skip":
            profile.onboarding_step = 7
            profile.save()
            return redirect("accounts:onboarding_summary")
        
        if action == "back":
            return redirect("accounts:onboarding_diagnosis")
        
        form = OnboardingMedicationStatusForm(request.POST)
        if form.is_valid():
            status = form.cleaned_data.get("has_prescribed_medication", "")
            profile.has_prescribed_medication = status
            profile.onboarding_step = 7
            profile.save()
            
            # Conditional routing: only ask about medications if user said "yes"
            if status == "yes":
                return redirect("accounts:onboarding_medication_select")
            else:
                return redirect("accounts:onboarding_summary")
    else:
        form = OnboardingMedicationStatusForm(
            initial={"has_prescribed_medication": profile.has_prescribed_medication}
        )
    
    context = get_onboarding_context(6)
    context["form"] = form
    context["can_skip"] = True
    context["can_go_back"] = True
    context["medication_options"] = [
        {"value": "yes", "label": "Yes", "description": "I've been prescribed treatment"},
        {"value": "no", "label": "No", "description": "I haven't been prescribed anything"},
        {"value": "prefer_not_to_say", "label": "Prefer not to say", "description": ""},
    ]
    return render(request, "accounts/onboarding/medication_status.html", context)


@login_required
def onboarding_medication_select(request):
    """Step 8: Select medications (conditional - only if prescribed)."""
    profile = request.user.profile
    
    # Get existing user medications for initial state
    existing_meds = list(request.user.medications.values_list("medication_key", flat=True))
    
    if request.method == "POST":
        action = request.POST.get("action", "next")
        
        if action == "skip":
            profile.onboarding_step = 8
            profile.save()
            return redirect("accounts:onboarding_summary")
        
        if action == "back":
            return redirect("accounts:onboarding_medication_status")
        
        form = OnboardingMedicationSelectForm(request.POST)
        if form.is_valid():
            selected = form.cleaned_data.get("selected_medications", [])
            custom = form.cleaned_data.get("custom_medication", "").strip()
            
            # Clear existing medications from onboarding (keep any added later)
            request.user.medications.filter(medication_key__in=[
                key for key, _, _ in COMMON_MEDICATIONS
            ]).delete()
            
            # Create medications for selected items
            has_antihistamine = False
            has_biologic = False
            
            for med_key in selected:
                # Find medication type from COMMON_MEDICATIONS
                med_type = "other"
                for key, label, mtype in COMMON_MEDICATIONS:
                    if key == med_key:
                        med_type = mtype
                        break
                
                UserMedication.objects.create(
                    user=request.user,
                    medication_key=med_key,
                    medication_type=med_type,
                )
                
                if med_type == "antihistamine":
                    has_antihistamine = True
                elif med_type == "biologic":
                    has_biologic = True
            
            # Handle custom medication
            if custom:
                UserMedication.objects.create(
                    user=request.user,
                    custom_name=custom,
                    medication_type="other",
                )
            
            profile.onboarding_step = 8
            profile.save()
            
            # Store what we found for the details step
            request.session["onboarding_has_antihistamine"] = has_antihistamine
            request.session["onboarding_has_biologic"] = has_biologic
            
            # Route to details if user has antihistamine or biologic
            if has_antihistamine or has_biologic:
                return redirect("accounts:onboarding_medication_details")
            else:
                return redirect("accounts:onboarding_summary")
    else:
        form = OnboardingMedicationSelectForm(initial={"selected_medications": existing_meds})
    
    # Build medication options grouped by type
    antihistamines = [
        {"key": key, "label": label}
        for key, label, mtype in COMMON_MEDICATIONS if mtype == "antihistamine"
    ]
    biologics = [
        {"key": key, "label": label}
        for key, label, mtype in COMMON_MEDICATIONS if mtype == "biologic"
    ]
    
    context = get_onboarding_context(7)
    context["form"] = form
    context["can_skip"] = True
    context["can_go_back"] = True
    context["antihistamines"] = antihistamines
    context["biologics"] = biologics
    return render(request, "accounts/onboarding/medication_select.html", context)


@login_required
def onboarding_medication_details(request):
    """Step 9: Medication details (dose/frequency for antihistamines, schedule for biologics)."""
    profile = request.user.profile
    
    # Check what types of medications user selected
    has_antihistamine = request.session.get("onboarding_has_antihistamine", False)
    has_biologic = request.session.get("onboarding_has_biologic", False)
    
    # Or check from database
    if not has_antihistamine and not has_biologic:
        user_meds = request.user.medications.all()
        has_antihistamine = user_meds.filter(medication_type="antihistamine").exists()
        has_biologic = user_meds.filter(medication_type="biologic").exists()
    
    if request.method == "POST":
        action = request.POST.get("action", "next")
        
        if action == "skip":
            profile.onboarding_step = 9
            profile.save()
            return redirect("accounts:onboarding_summary")
        
        if action == "back":
            return redirect("accounts:onboarding_medication_select")
        
        # Process antihistamine details
        if has_antihistamine:
            ah_form = OnboardingAntihistamineDetailsForm(request.POST, prefix="ah")
            if ah_form.is_valid():
                # Update all user's antihistamines with this info
                dose = ah_form.cleaned_data.get("dose_amount")
                unit = ah_form.cleaned_data.get("dose_unit", "mg")
                freq = ah_form.cleaned_data.get("frequency_per_day")
                
                request.user.medications.filter(medication_type="antihistamine").update(
                    dose_amount=dose,
                    dose_unit=unit,
                    frequency_per_day=freq,
                )
        
        # Process biologic/injection details
        if has_biologic:
            inj_form = OnboardingInjectionDetailsForm(request.POST, prefix="inj")
            if inj_form.is_valid():
                last_date = inj_form.cleaned_data.get("last_injection_date")
                frequency = inj_form.cleaned_data.get("injection_frequency", "")
                
                request.user.medications.filter(medication_type="biologic").update(
                    last_injection_date=last_date,
                    injection_frequency=frequency,
                )
        
        profile.onboarding_step = 9
        profile.save()
        
        # Clean up session
        request.session.pop("onboarding_has_antihistamine", None)
        request.session.pop("onboarding_has_biologic", None)
        
        return redirect("accounts:onboarding_summary")
    else:
        ah_form = OnboardingAntihistamineDetailsForm(prefix="ah")
        inj_form = OnboardingInjectionDetailsForm(prefix="inj")
    
    context = get_onboarding_context(8)
    context["can_skip"] = True
    context["can_go_back"] = True
    context["has_antihistamine"] = has_antihistamine
    context["has_biologic"] = has_biologic
    context["ah_form"] = ah_form
    context["inj_form"] = inj_form
    
    # Get medication names for display
    if has_antihistamine:
        context["antihistamine_names"] = list(
            request.user.medications.filter(medication_type="antihistamine")
            .values_list("medication_key", flat=True)
        )
    if has_biologic:
        context["biologic_names"] = list(
            request.user.medications.filter(medication_type="biologic")
            .values_list("medication_key", flat=True)
        )
    
    return render(request, "accounts/onboarding/medication_details.html", context)


@login_required
def onboarding_summary(request):
    """Step 10: Summary of what you've shared."""
    profile = request.user.profile
    
    if request.method == "POST":
        action = request.POST.get("action", "next")
        
        if action == "back":
            # Go back to medications or diagnosis depending on path
            if profile.has_prescribed_medication == "yes":
                return redirect("accounts:onboarding_medication_details")
            else:
                return redirect("accounts:onboarding_medication_status")
        
        profile.onboarding_step = 10
        profile.save()
        return redirect("accounts:onboarding_privacy")
    
    # Build summary data
    summary_items = []
    
    # Full name from User model
    full_name = f"{request.user.first_name} {request.user.last_name}".strip()
    if full_name:
        summary_items.append({
            "label": "Name",
            "value": full_name,
            "icon": "👤",
        })
    
    # DOB and age from profile
    if profile.date_of_birth:
        from datetime import date
        dob_str = profile.date_of_birth.strftime("%B %d, %Y")
        # Calculate current age
        today = date.today()
        age = today.year - profile.date_of_birth.year - ((today.month, today.day) < (profile.date_of_birth.month, profile.date_of_birth.day))
        summary_items.append({
            "label": "Date of Birth",
            "value": f"{dob_str} ({age} years old)",
            "icon": "🎂",
        })
    elif profile.age:
        summary_items.append({
            "label": "Age",
            "value": f"{profile.age} years old",
            "icon": "🎂",
        })
    
    if profile.gender and profile.gender != "prefer_not_to_say":
        gender_display = {
            "male": "Male",
            "female": "Female",
            "non_binary": "Non-binary",
        }.get(profile.gender, profile.gender)
        summary_items.append({
            "label": "Gender",
            "value": gender_display,
            "icon": "🧑",
        })
    
    if profile.csu_diagnosis:
        diagnosis_display = {
            "yes": "Diagnosed with CSU",
            "no": "Not diagnosed",
            "unsure": "Still figuring it out",
        }.get(profile.csu_diagnosis, "")
        if diagnosis_display:
            summary_items.append({
                "label": "CSU Status",
                "value": diagnosis_display,
                "icon": "🩺",
            })
    
    # Get medications
    medications = list(request.user.medications.all())
    if medications:
        med_names = []
        for med in medications:
            if med.custom_name:
                med_names.append(med.custom_name)
            elif med.medication_key:
                # Find display name from COMMON_MEDICATIONS
                for key, label, _ in COMMON_MEDICATIONS:
                    if key == med.medication_key:
                        med_names.append(label)
                        break
        if med_names:
            summary_items.append({
                "label": "Medications",
                "value": ", ".join(med_names),
                "icon": "💊",
            })
    elif profile.has_prescribed_medication == "no":
        summary_items.append({
            "label": "Medications",
            "value": "No prescribed treatment",
            "icon": "💊",
        })
    
    context = get_onboarding_context(9)
    context["summary_items"] = summary_items
    context["can_go_back"] = True
    context["has_data"] = len(summary_items) > 0
    return render(request, "accounts/onboarding/summary.html", context)


@login_required
def onboarding_privacy(request):
    """Step 11: Privacy and data consent."""
    profile = request.user.profile
    
    if request.method == "POST":
        action = request.POST.get("action", "next")
        
        if action == "back":
            return redirect("accounts:onboarding_summary")
        
        form = OnboardingPrivacyConsentForm(request.POST)
        if form.is_valid():
            profile.privacy_consent_given = form.cleaned_data.get("privacy_consent", False)
            profile.allow_data_collection = form.cleaned_data.get("allow_analytics", False)
            
            if profile.privacy_consent_given:
                profile.privacy_consent_date = timezone.now()
            
            profile.onboarding_step = 11
            profile.save()
            return redirect("accounts:onboarding_reminders")
    else:
        form = OnboardingPrivacyConsentForm(initial={
            "privacy_consent": profile.privacy_consent_given,
            "allow_analytics": getattr(profile, "allow_data_collection", False),
        })
    
    context = get_onboarding_context(10)
    context["form"] = form
    context["can_go_back"] = True
    return render(request, "accounts/onboarding/privacy.html", context)


@login_required
def onboarding_reminders(request):
    """Step 12: Optional reminder setup with timezone."""
    profile = request.user.profile
    
    # Import here to avoid circular imports
    from notifications.models import ReminderPreferences
    
    # Get or create reminder preferences
    reminder_prefs, _ = ReminderPreferences.objects.get_or_create(user=request.user)
    
    if request.method == "POST":
        action = request.POST.get("action", "next")
        
        if action == "skip":
            profile.onboarding_step = 12
            profile.save()
            return redirect("accounts:onboarding_complete")
        
        if action == "back":
            return redirect("accounts:onboarding_privacy")
        
        form = OnboardingReminderForm(request.POST)
        if form.is_valid():
            enable = form.cleaned_data.get("enable_reminders") == "yes"
            reminder_prefs.enabled = enable
            
            if enable:
                reminder_time = form.cleaned_data.get("reminder_time")
                if reminder_time:
                    reminder_prefs.time_of_day = reminder_time
            
            # Save timezone preference
            timezone_choice = form.cleaned_data.get("timezone")
            if timezone_choice:
                profile.default_timezone = timezone_choice
            
            reminder_prefs.save()
            profile.onboarding_step = 12
            profile.save()
            return redirect("accounts:onboarding_complete")
    else:
        form = OnboardingReminderForm(initial={
            "enable_reminders": "yes" if reminder_prefs.enabled else "no",
            "reminder_time": reminder_prefs.time_of_day,
            "timezone": profile.default_timezone or "Europe/London",
        })
    
    context = get_onboarding_context(11)
    context["form"] = form
    context["can_skip"] = True
    context["can_go_back"] = True
    return render(request, "accounts/onboarding/reminders.html", context)


@login_required
def onboarding_complete(request):
    """Final step: All set! Welcome to the app."""
    profile = request.user.profile
    profile.onboarding_completed = True
    profile.onboarding_step = 13
    profile.save()
    
    # Get some stats for the completion screen
    from notifications.models import ReminderPreferences
    
    reminder_prefs = ReminderPreferences.objects.filter(user=request.user).first()
    reminders_enabled = reminder_prefs.enabled if reminder_prefs else False
    reminder_time = reminder_prefs.time_of_day if reminder_prefs else None
    
    context = get_onboarding_context(12)
    context["display_name"] = profile.display_name_or_email
    context["reminders_enabled"] = reminders_enabled
    context["reminder_time"] = reminder_time
    return render(request, "accounts/onboarding/complete.html", context)
