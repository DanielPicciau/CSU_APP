# CSU Tracker - PythonAnywhere Deployment Guide

Complete deployment guide for **CSU-WebFlareUK.pythonanywhere.com**

---

## Table of Contents
1. [Clone Repository](#1-clone-repository)
2. [Create Virtual Environment](#2-create-virtual-environment)
3. [Install Dependencies](#3-install-dependencies)
4. [Configure Environment Variables](#4-configure-environment-variables)
5. [Configure WSGI File](#5-configure-wsgi-file)
6. [Configure Static Files](#6-configure-static-files)
7. [Set Up Database](#7-set-up-database)
8. [Configure Web App Settings](#8-configure-web-app-settings)
9. [Push Notifications Setup](#9-push-notifications-setup)
10. [Reload and Test](#10-reload-and-test)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Clone Repository

Open a **Bash console** on PythonAnywhere (Dashboard → Consoles → Bash) and run:

```bash
cd ~
git clone https://github.com/DanielPicciau/CSU_APP.git
cd CSU_APP
```

---

## 2. Create Virtual Environment

Still in the Bash console:

```bash
cd ~/CSU_APP
python3.13 -m venv .venv
source .venv/bin/activate
```

---

## 3. Install Dependencies

With the virtualenv activated:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

If you get errors, install from pyproject.toml:

```bash
pip install -e .
```

---

## 4. Configure Environment Variables

Create the `.env` file:

```bash
cd ~/CSU_APP
nano .env
```

Paste this content (modify as needed):

```env
# Django Settings
DEBUG=False
SECRET_KEY=your-super-secret-key-generate-a-new-one
FERNET_KEYS=your-fernet-key
ALLOWED_HOSTS=csu-webflareuk.pythonanywhere.com,www.csu-webflareuk.pythonanywhere.com

# Database (SQLite for PythonAnywhere free tier)
DATABASE_URL=sqlite:////home/WebFlareUK/CSU_APP/db.sqlite3

# Redis Cloud Configuration
# Get these from your Redis Cloud dashboard (cloud.redis.io)
# Format: redis://default:<PASSWORD>@<HOST>:<PORT>
REDIS_URL=redis://default:YOUR_PASSWORD@YOUR_HOST:YOUR_PORT
CELERY_BROKER_URL=redis://default:YOUR_PASSWORD@YOUR_HOST:YOUR_PORT
CELERY_RESULT_BACKEND=redis://default:YOUR_PASSWORD@YOUR_HOST:YOUR_PORT

# Web Push VAPID Keys (KEEP THESE - they're already generated)
VAPID_PRIVATE_KEY=RuODY2Iwc8WGs3EiioNVvJvUrrTrujlWZSbdnw4dw30
VAPID_PUBLIC_KEY=BNCuiOAvDsI0x3p7890t26bH85TTXLdjjs8eBwzZ2m9rxAsHPgH_9rcBMl_fvF5hHmDJUm3bBH5AwcULoKxYAIc
VAPID_ADMIN_EMAIL=your-email@example.com

# CSU Score Configuration
CSU_MAX_SCORE=42

# Security
CSRF_TRUSTED_ORIGINS=https://csu-webflareuk.pythonanywhere.com
```

Save with `Ctrl+O`, Enter, then `Ctrl+X` to exit.

**Generate a new SECRET_KEY:**

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the output and paste it as your SECRET_KEY value.

**Generate a new FERNET key:**

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output and paste it as your FERNET_KEYS value.

---

## 5. Configure WSGI File

Go to **Web** tab → Click on the WSGI configuration file link:
`/var/www/csu-webflareuk_pythonanywhere_com_wsgi.py`

**Delete everything** and replace with:

```python
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add your project directory to the sys.path
project_home = '/home/WebFlareUK/CSU_APP'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Load environment variables from .env file
env_path = Path(project_home) / '.env'
load_dotenv(env_path)

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Import Django and get the WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

**Save the file.**

---

## 6. Configure Static Files

### In the Web tab, under "Static files":

Add these mappings:

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/WebFlareUK/CSU_APP/staticfiles/` |

### Collect static files (in Bash console):

```bash
cd ~/CSU_APP
source .venv/bin/activate
python manage.py collectstatic --noinput
```

---

## 7. Set Up Database

Run migrations:

```bash
cd ~/CSU_APP
source .venv/bin/activate
python manage.py migrate
```

Create a superuser (admin account):

```bash
python manage.py createsuperuser
```

---

## 8. Configure Web App Settings

In the **Web** tab, set:

| Setting | Value |
|---------|-------|
| **Source code** | `/home/WebFlareUK/CSU_APP` |
| **Working directory** | `/home/WebFlareUK/CSU_APP` |
| **Virtualenv** | `/home/WebFlareUK/CSU_APP/.venv` |
| **Python version** | 3.13 |

### Security Settings:

- ✅ **Force HTTPS**: Enable this (required for push notifications!)

---

## 9. Push Notifications Setup

Push notifications require HTTPS (which PythonAnywhere provides).

### Important Notes:

1. **HTTPS is enabled** by default on PythonAnywhere ✅
2. **Force HTTPS** must be turned ON in the Web tab
3. **Service Worker** requires HTTPS to work
4. On **iPhone**: User must "Add to Home Screen" and open from there

### Test notifications:
1. Go to `https://csu-webflareuk.pythonanywhere.com`
2. Register/Login
3. Go to Notifications settings
4. Click "Enable Notifications" and allow
5. Click "Send Test Notification"

---

## 10. Reload and Test

1. Go to the **Web** tab
2. Click the big green **"Reload"** button
3. Visit: `https://csu-webflareuk.pythonanywhere.com`

### If you see errors, check the logs:
- **Error log**: Shows Python errors
- **Server log**: Shows WSGI issues
- **Access log**: Shows requests

---

## 11. Troubleshooting

### "ModuleNotFoundError: No module named 'XXX'"

Make sure virtualenv path is correct:
```
/home/WebFlareUK/CSU_APP/.venv
```

Install missing package:
```bash
source ~/CSU_APP/.venv/bin/activate
pip install <package-name>
```

### "Invalid HTTP_HOST header"

Add the domain to ALLOWED_HOSTS in `.env`:
```
ALLOWED_HOSTS=csu-webflareuk.pythonanywhere.com
```

### Static files not loading (404)

1. Check the static file mapping URL is `/static/` (with trailing slash)
2. Run `python manage.py collectstatic --noinput`
3. Reload the web app

### "CSRF verification failed"

Add to `.env`:
```
CSRF_TRUSTED_ORIGINS=https://csu-webflareuk.pythonanywhere.com
```

### Push notifications not working

1. Make sure **Force HTTPS** is enabled
2. On iPhone: Must be opened from Home Screen (Add to Home Screen first)
3. Check browser console for errors (F12 → Console)

### Database errors

Reset and migrate:
```bash
cd ~/CSU_APP
source .venv/bin/activate
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

---

## Quick Update Commands

When you push updates to GitHub, run on PythonAnywhere:

```bash
cd ~/CSU_APP
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

Then click **Reload** in the Web tab.

---

## Summary Checklist

- [ ] Clone repo to `/home/WebFlareUK/CSU_APP`
- [ ] Create virtualenv at `/home/WebFlareUK/CSU_APP/.venv`
- [ ] Install dependencies with pip
- [ ] Create `.env` file with production settings
- [ ] Update WSGI file
- [ ] Add static files mapping: `/static/` → `/home/WebFlareUK/CSU_APP/staticfiles/`
- [ ] Set virtualenv path in Web tab
- [ ] Run `migrate` and `collectstatic`
- [ ] Enable **Force HTTPS**
- [ ] Click **Reload**
- [ ] Test the site!

---

## Your URLs

- **Main site**: https://csu-webflareuk.pythonanywhere.com
- **Admin**: https://csu-webflareuk.pythonanywhere.com/admin/
- **API**: https://csu-webflareuk.pythonanywhere.com/api/

---

*Generated for CSU Tracker deployment on PythonAnywhere*
