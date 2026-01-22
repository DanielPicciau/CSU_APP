# CSU Tracker

A mobile-first Progressive Web App (PWA) for tracking Chronic Spontaneous Urticaria (CSU) symptoms daily. Built with Django, designed to run beautifully on iPhone and scale for public use.

## Features

- 📱 **Mobile-First PWA**: Works like a native app on iPhone when added to Home Screen
- 📊 **Daily CSU Logging**: Track itch severity, hive count, and antihistamine use
- 📈 **UAS7 Calculation**: Automatic weekly Urticaria Activity Score
- 🔔 **Push Notifications**: Daily reminders to log your symptoms
- 📅 **History & Charts**: Visual overview of your symptom patterns
- 🔐 **Secure Auth**: Email-based authentication with session and JWT support

## Tech Stack

- **Backend**: Python 3.12+, Django 5+, Django REST Framework
- **Database**: PostgreSQL 16
- **Task Queue**: Celery + Redis + Celery Beat
- **Notifications**: Web Push (VAPID)
- **Frontend**: Django Templates + HTMX + Tailwind CSS
- **Development**: Docker Compose, Ruff

## Project Structure

```
CSU APP/
├── core/                   # Django project settings
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   ├── wsgi.py
│   └── asgi.py
├── accounts/               # User accounts app
│   ├── models.py          # User, Profile
│   ├── views.py           # Login, Register, Profile views
│   ├── api_views.py       # REST API endpoints
│   ├── serializers.py
│   ├── forms.py
│   ├── urls.py
│   ├── api_urls.py
│   └── admin.py
├── tracking/               # CSU tracking app
│   ├── models.py          # DailyEntry
│   ├── views.py           # Log entry, History views
│   ├── api_views.py       # REST API endpoints
│   ├── serializers.py
│   ├── forms.py
│   ├── urls.py
│   ├── api_urls.py
│   └── admin.py
├── notifications/          # Push notifications app
│   ├── models.py          # PushSubscription, ReminderPreferences
│   ├── views.py           # Notification settings views
│   ├── api_views.py       # REST API endpoints
│   ├── tasks.py           # Celery tasks for reminders
│   ├── push.py            # Web Push utility functions
│   ├── serializers.py
│   ├── urls.py
│   ├── api_urls.py
│   └── admin.py
├── templates/              # Django templates
│   ├── base.html
│   ├── accounts/
│   ├── tracking/
│   ├── notifications/
│   └── pwa/
├── static/                 # Static files
│   └── icons/
├── docker-compose.yml
├── pyproject.toml
├── manage.py
├── .env.example
└── README.md
```

## Quick Start (macOS)

### Prerequisites

- Python 3.12+
- Docker Desktop (for PostgreSQL and Redis)
- Git

### 1. Clone and Setup

```bash
# Navigate to project directory
cd "/Users/admin/Library/Mobile Documents/com~apple~CloudDocs/CSU APP"

# Create and activate virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
```

### 2. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Generate a secure secret key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Edit .env and set:
# - SECRET_KEY (from above command)
# - VAPID keys (see below)
```

### 3. Generate VAPID Keys

```bash
# In Python shell
python -c "
from py_vapid import Vapid
v = Vapid()
v.generate_keys()
print('VAPID_PRIVATE_KEY=' + v.private_pem().decode().replace('\n', ''))
print('VAPID_PUBLIC_KEY=' + v.public_key)
"
```

Add the generated keys to your `.env` file.

### 4. Start Services

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Wait for services to be healthy
docker-compose ps
```

### 5. Initialize Database

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

### 6. Run Development Server

```bash
# Terminal 1: Django development server
python manage.py runserver 0.0.0.0:8000

# Terminal 2: Celery worker
celery -A core worker -l INFO

# Terminal 3: Celery Beat scheduler
celery -A core beat -l INFO
```

### 7. Access the App

- **Web App**: http://localhost:8000
- **Admin**: http://localhost:8000/admin
- **API Root**: http://localhost:8000/api/

## iPhone PWA Installation

For the best experience and working push notifications on iPhone:

1. Open Safari and navigate to your deployed app URL
2. Tap the **Share** button (square with arrow)
3. Select **"Add to Home Screen"**
4. Tap **Add**
5. Open the app from your Home Screen
6. Enable notifications when prompted

> **Note**: Web Push on iOS requires Safari 16.4+ and the app must be installed to the Home Screen.

## API Documentation

### Authentication

The app supports both session-based (for web UI) and JWT (for API clients) authentication.

#### Get JWT Token

```bash
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "yourpassword"}'
```

Response:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

Use the access token in subsequent requests:
```bash
-H "Authorization: Bearer <access_token>"
```

### Accounts API

#### Register

```bash
curl -X POST http://localhost:8000/api/accounts/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123",
    "password_confirm": "securepassword123"
  }'
```

#### Get Current User

```bash
curl http://localhost:8000/api/accounts/me/ \
  -H "Authorization: Bearer <token>"
```

Response:
```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "",
  "last_name": "",
  "profile": {
    "date_format": "YYYY-MM-DD",
    "default_timezone": "America/New_York",
    "created_at": "2026-01-21T10:00:00Z",
    "updated_at": "2026-01-21T10:00:00Z"
  },
  "date_joined": "2026-01-21T10:00:00Z"
}
```

### Tracking API

#### Create/Update Today's Entry

```bash
curl -X POST http://localhost:8000/api/tracking/today/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "score": 4,
    "itch_score": 2,
    "hive_count_score": 2,
    "took_antihistamine": true,
    "notes": "Symptoms worse in evening"
  }'
```

Response:
```json
{
  "id": 1,
  "date": "2026-01-21",
  "score": 4,
  "itch_score": 2,
  "hive_count_score": 2,
  "notes": "Symptoms worse in evening",
  "took_antihistamine": true,
  "created_at": "2026-01-21T20:00:00Z",
  "updated_at": "2026-01-21T20:00:00Z"
}
```

#### Get Today's Entry

```bash
curl http://localhost:8000/api/tracking/today/ \
  -H "Authorization: Bearer <token>"
```

#### List Entries (with date filter)

```bash
curl "http://localhost:8000/api/tracking/entries/?start_date=2026-01-01&end_date=2026-01-21" \
  -H "Authorization: Bearer <token>"
```

Response:
```json
{
  "count": 15,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 15,
      "date": "2026-01-21",
      "score": 4,
      "itch_score": 2,
      "hive_count_score": 2,
      "notes": "",
      "took_antihistamine": false,
      "created_at": "2026-01-21T20:00:00Z",
      "updated_at": "2026-01-21T20:00:00Z"
    }
  ]
}
```

#### Get Adherence Metrics

```bash
curl "http://localhost:8000/api/tracking/adherence/?days=7" \
  -H "Authorization: Bearer <token>"
```

Response:
```json
{
  "period_days": 7,
  "entries_count": 5,
  "adherence_percentage": 71.43,
  "average_score": 3.2,
  "missing_dates": ["2026-01-15", "2026-01-18"]
}
```

#### Get Weekly Stats (UAS7)

```bash
curl "http://localhost:8000/api/tracking/weekly/?weeks=4" \
  -H "Authorization: Bearer <token>"
```

Response:
```json
[
  {
    "week_start": "2026-01-15",
    "week_end": "2026-01-21",
    "uas7_score": 22,
    "entries_count": 7,
    "complete": true
  },
  {
    "week_start": "2026-01-08",
    "week_end": "2026-01-14",
    "uas7_score": 18,
    "entries_count": 6,
    "complete": false
  }
]
```

### Notifications API

#### Subscribe to Push

```bash
curl -X POST http://localhost:8000/api/notifications/subscribe/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "endpoint": "https://fcm.googleapis.com/fcm/send/...",
    "keys": {
      "p256dh": "BNcRd...",
      "auth": "tBHI..."
    }
  }'
```

#### Get/Update Reminder Preferences

```bash
# GET
curl http://localhost:8000/api/notifications/preferences/ \
  -H "Authorization: Bearer <token>"

# PUT
curl -X PUT http://localhost:8000/api/notifications/preferences/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "time_of_day": "20:00",
    "timezone": "America/New_York"
  }'
```

#### Send Test Notification

```bash
curl -X POST http://localhost:8000/api/notifications/test/ \
  -H "Authorization: Bearer <token>"
```

## Endpoint Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/token/` | Get JWT tokens |
| POST | `/api/token/refresh/` | Refresh JWT token |
| POST | `/api/accounts/register/` | Register new user |
| GET/PUT | `/api/accounts/me/` | Get/update current user |
| PUT | `/api/accounts/profile/` | Update profile |
| POST | `/api/accounts/password/change/` | Change password |
| GET/POST | `/api/tracking/entries/` | List/create entries |
| GET/PUT/DELETE | `/api/tracking/entries/<date>/` | Entry by date |
| GET/POST | `/api/tracking/today/` | Today's entry |
| GET | `/api/tracking/adherence/` | Adherence metrics |
| GET | `/api/tracking/weekly/` | Weekly UAS7 stats |
| POST | `/api/notifications/subscribe/` | Subscribe to push |
| POST | `/api/notifications/unsubscribe/` | Unsubscribe |
| GET/PUT | `/api/notifications/preferences/` | Reminder settings |
| POST | `/api/notifications/test/` | Send test notification |

## Development

### Code Quality

```bash
# Lint and format
ruff check .
ruff format .

# Run tests
pytest

# Run tests with coverage
pytest --cov=. --cov-report=html
```

### Database Management

```bash
# Create migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Reset database (development only)
docker-compose down -v
docker-compose up -d
python manage.py migrate
```

### Celery Tasks

```bash
# Run worker with verbose output
celery -A core worker -l DEBUG

# Run beat scheduler
celery -A core beat -l INFO

# Monitor with Flower (install: pip install flower)
celery -A core flower
```

## Production Deployment

### Environment Variables

Set these in production:

```bash
DEBUG=False
SECRET_KEY=<strong-random-key>
FERNET_KEYS=<fernet-key>
ALLOWED_HOSTS=yourdomain.com
DATABASE_URL=postgres://user:pass@host:5432/dbname
REDIS_URL=redis://host:6379/0
VAPID_PRIVATE_KEY=<your-private-key>
VAPID_PUBLIC_KEY=<your-public-key>
VAPID_ADMIN_EMAIL=admin@yourdomain.com
SECURE_SSL_REDIRECT=True
CSRF_TRUSTED_ORIGINS=https://yourdomain.com
CORS_ALLOWED_ORIGINS=https://yourdomain.com
```

### HTTPS Requirement

TLS is required in production. Ensure your reverse proxy (nginx) terminates SSL and forwards `X-Forwarded-Proto: https` so Django enforces HTTPS and HSTS correctly.

### Encryption at Rest

Sensitive fields are encrypted with Fernet before being stored in the database. Set `FERNET_KEYS` (comma-separated for rotation) and keep it secret. Without this key, encrypted data cannot be recovered.

### Static Files

```bash
python manage.py collectstatic --noinput
```

Serve from `/staticfiles/` with nginx or WhiteNoise (included).

## Troubleshooting

### Push notifications not working on iPhone

1. Ensure the app is added to Home Screen
2. Check Safari version is 16.4+
3. Verify VAPID keys are configured correctly
4. Check notification permissions in iOS Settings

### Celery tasks not running

1. Verify Redis is running: `docker-compose ps`
2. Check worker logs: `celery -A core worker -l DEBUG`
3. Ensure beat scheduler is running for periodic tasks

### Database connection errors

1. Check PostgreSQL is running: `docker-compose ps`
2. Verify DATABASE_URL in `.env`
3. Check database exists: `docker-compose exec db psql -U csu_user -d csu_tracker`

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request
