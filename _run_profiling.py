"""
Temporary profiling script — hit the 4 slow endpoints as an authenticated
user and let the RequestTimingMiddleware print the diagnostic output.

Usage:
    .venv/bin/python _run_profiling.py
"""
import os
import sys
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
sys.path.insert(0, os.path.dirname(__file__))

import django
django.setup()

# Allow test client's default Host header
from django.conf import settings
if "testserver" not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append("testserver")

from django.test import RequestFactory, Client
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.get(pk=1)
# Ensure profile has onboarding_completed so middleware doesn't redirect
try:
    profile = user.profile
    if not profile.onboarding_completed:
        profile.onboarding_completed = True
        profile.save(update_fields=["onboarding_completed"])
        print(f"Set onboarding_completed=True for {user.email}")
except Exception:
    pass
client = Client(raise_request_exception=False)
client.force_login(user)

ENDPOINTS = [
    "/tracking/",           # today_view
    "/tracking/insights/",  # insights_view
    "/tracking/history/",   # history_view
    "/tracking/log/",       # log_entry_view
]

print("\n" + "=" * 72)
print("  PROFILING RUN  —  All times are server-side wall-clock")
print("=" * 72)

for url in ENDPOINTS:
    print(f"\n>>> Hitting {url} ...")
    t0 = time.perf_counter()
    resp = client.get(url)
    wall = (time.perf_counter() - t0) * 1000
    print(f"<<< {url}  status={resp.status_code}  wall={wall:.1f} ms")

# Second pass — warm caches
print("\n" + "=" * 72)
print("  SECOND PASS (warm caches)")
print("=" * 72)

for url in ENDPOINTS:
    print(f"\n>>> Hitting {url} ...")
    t0 = time.perf_counter()
    resp = client.get(url)
    wall = (time.perf_counter() - t0) * 1000
    print(f"<<< {url}  status={resp.status_code}  wall={wall:.1f} ms")

print("\n" + "=" * 72)
print("  DONE")
print("=" * 72)
