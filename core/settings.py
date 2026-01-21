"""
Django settings for CSU Tracker project.
"""

import os
from datetime import timedelta
from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Environment variables
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CSU_MAX_SCORE=(int, 42),
)

# Read .env file
environ.Env.read_env(BASE_DIR / ".env")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG")

ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_celery_beat",
    # Local apps
    "accounts.apps.AccountsConfig",
    "tracking.apps.TrackingConfig",
    "notifications.apps.NotificationsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Security middleware
    "core.middleware.SecurityHeadersMiddleware",
    "core.middleware.RateLimitMiddleware",
    "core.middleware.RequestValidationMiddleware",
    "core.middleware.AuditMiddleware",
    # Onboarding redirect for new users
    "core.middleware.OnboardingMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.pwa_context",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

# Database
DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres://csu_user:csu_password@localhost:5432/csu_tracker")
}

# Custom User Model
AUTH_USER_MODEL = "accounts.User"

# Password validation - Medical-grade requirements
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "core.validators.MedicalGradePasswordValidator"},
    {"NAME": "core.validators.NoPersonalInfoValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework - Secure configuration
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/minute",
        "user": "100/minute",
    },
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 30,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ] if not DEBUG else [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

# JWT Settings - Secure configuration
# SECURITY: Use a separate signing key from SECRET_KEY for defense in depth
JWT_SIGNING_KEY = env("JWT_SIGNING_KEY", default="")
if not JWT_SIGNING_KEY:
    import warnings
    if not DEBUG:
        warnings.warn(
            "JWT_SIGNING_KEY not set! Using SECRET_KEY is insecure in production. "
            "Generate a separate key with: python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\"",
            SecurityWarning
        )
    JWT_SIGNING_KEY = SECRET_KEY

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),  # Shorter for security
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),  # Shorter for security
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": JWT_SIGNING_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
}

# CORS Settings
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[
    "http://localhost:8000",
    "http://127.0.0.1:8000",
])
CORS_ALLOW_CREDENTIALS = True

# CSRF Settings
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[
    "http://localhost:8000",
    "http://127.0.0.1:8000",
])

# In debug mode, also trust the current request's origin for CSRF
if DEBUG:
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False
else:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True

# Celery Configuration
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Redis Cloud uses SSL - detect and configure
# SECURITY: Always require SSL certificate verification in production
if CELERY_BROKER_URL.startswith("rediss://"):
    import ssl
    ssl_cert_reqs = ssl.CERT_NONE if DEBUG else ssl.CERT_REQUIRED
    CELERY_BROKER_USE_SSL = {"ssl_cert_reqs": ssl_cert_reqs}
    CELERY_REDIS_BACKEND_USE_SSL = {"ssl_cert_reqs": ssl_cert_reqs}

# Web Push VAPID Configuration
VAPID_PRIVATE_KEY = env("VAPID_PRIVATE_KEY", default="")
VAPID_PUBLIC_KEY = env("VAPID_PUBLIC_KEY", default="")
VAPID_ADMIN_EMAIL = env("VAPID_ADMIN_EMAIL", default="")

# Validate VAPID email in production
if not DEBUG and VAPID_PRIVATE_KEY and not VAPID_ADMIN_EMAIL:
    import warnings
    warnings.warn(
        "VAPID_ADMIN_EMAIL is not set. Push notifications may fail without a valid contact email.",
        UserWarning
    )

# Cron Webhook Secret (for external cron services like cron-job.org)
CRON_WEBHOOK_SECRET = env("CRON_WEBHOOK_SECRET", default="")
if not DEBUG and not CRON_WEBHOOK_SECRET:
    import warnings
    warnings.warn(
        "CRON_WEBHOOK_SECRET is not set. Cron endpoints will reject all requests.",
        UserWarning
    )

# CSU Configuration
CSU_MAX_SCORE = env("CSU_MAX_SCORE")

# Login/Logout URLs
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# Session settings for PWA
# SECURITY: 7 days is appropriate for medical-grade app with sensitive health data
# Users will need to re-authenticate weekly for enhanced security
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # 7 days
SESSION_COOKIE_SAMESITE = "Lax"

# =============================================================================
# SECURITY SETTINGS - Medical Grade
# =============================================================================

# HTTPS/SSL Settings (enforced in production)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Cookie Security
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# X-Frame-Options
X_FRAME_OPTIONS = 'DENY'

# Content Type Sniffing
SECURE_CONTENT_TYPE_NOSNIFF = True

# XSS Filter
SECURE_BROWSER_XSS_FILTER = True

# Referrer Policy
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# =============================================================================
# LOGGING CONFIGURATION - Audit Compliance
# =============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'audit': {
            'format': '[AUDIT] {asctime} {message}',
            'style': '{',
        },
        'security': {
            'format': '[SECURITY] {asctime} {levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'audit_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'audit.log',
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 10,
            'formatter': 'audit',
        },
        'security_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 10,
            'formatter': 'security',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'audit': {
            'handlers': ['console', 'audit_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'security': {
            'handlers': ['console', 'security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
import os
import sys
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# Testing flag
TESTING = 'test' in sys.argv or 'pytest' in sys.modules
