
import os
import time
import django
from django.conf import settings
from django.test import Client

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
from django.conf import settings
# Patch middleware to include profiler
# We need to configure this BEFORE django.setup() fully initializes? 
# Actually settings are lazy.
if not settings.configured:
    # We can't easily modify settings before setup if we rely on DJANGO_SETTINGS_MODULE
    pass

django.setup()

# Now patch settings.MIDDLEWARE
settings.MIDDLEWARE = ["core.middleware_profiler.ProfilingMiddleware"] + list(settings.MIDDLEWARE)

def profile_homepage():
    print("Starting profiling for homepage request with Client...")
    client = Client(HTTP_HOST='localhost')
    
    # We need a user
    from accounts.models import User
    try:
        user = User.objects.first()
        if not user:
            print("No user found, creating one.")
            user = User.objects.create_user(email="test@example.com", password="password")
    except Exception as e:
        print(f"Error getting user: {e}")
        return

    print(f"Logging in as {user.email}...")
    client.force_login(user)
    
    start_time = time.time()
    response = client.get('/')
    end_time = time.time()
    
    print(f"Total time: {end_time - start_time:.4f} seconds")
    print(f"Response status: {response.status_code}")
    if response.status_code == 302:
        print(f"Redirect to: {response.url}")

    # Also try accessing 'today' page directly if we get redirected there
    if response.status_code == 302 and response.url == '/tracking/today/': # Assumption
         print("Following redirect...")
         start_time = time.time()
         response = client.get(response.url)
         end_time = time.time()
         print(f"Follow up request time: {end_time - start_time:.4f} seconds")

if __name__ == "__main__":
    profile_homepage()
