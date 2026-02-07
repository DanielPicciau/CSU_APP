"""Temp script to set test password and run profiling requests."""
import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()
u = User.objects.get(pk=1)
u.set_password("TestPass1234")
u.save()
print(f"Password set for {u.email}")
