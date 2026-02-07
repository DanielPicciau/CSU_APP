.PHONY: help install dev run migrate shell test lint format clean docker-up docker-down celery beat tailwind

# Default target
help:
	@echo "CSU Tracker - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install     Install dependencies"
	@echo "  make dev         Install dev dependencies"
	@echo "  make docker-up   Start PostgreSQL and Redis"
	@echo "  make docker-down Stop Docker services"
	@echo ""
	@echo "Development:"
	@echo "  make run         Run Django development server"
	@echo "  make celery      Run Celery worker"
	@echo "  make beat        Run Celery Beat scheduler"
	@echo "  make shell       Open Django shell"
	@echo "  make migrate     Run database migrations"
	@echo "  make migrations  Create new migrations"
	@echo "  make tailwind    Build Tailwind CSS (run after template changes)"
	@echo ""
	@echo "Quality:"
	@echo "  make lint        Run linter (ruff)"
	@echo "  make format      Format code (ruff)"
	@echo "  make test        Run tests"
	@echo ""
	@echo "Utilities:"
	@echo "  make superuser   Create superuser"
	@echo "  make static      Collect static files"
	@echo "  make icons       Generate PWA icons"
	@echo "  make clean       Remove cache files"

# Setup
install:
	pip install -e .

dev:
	pip install -e ".[dev]"

docker-up:
	docker-compose up -d
	@echo "Waiting for services..."
	@sleep 3
	docker-compose ps

docker-down:
	docker-compose down

# Development
run:
	python manage.py runserver 0.0.0.0:8000

celery:
	celery -A core worker -l INFO

beat:
	celery -A core beat -l INFO

shell:
	python manage.py shell

migrate:
	python manage.py migrate

migrations:
	python manage.py makemigrations

superuser:
	python manage.py createsuperuser

static:
	python manage.py collectstatic --noinput

icons:
	python generate_icons.py

tailwind:
	npx tailwindcss -i static/css/input.css -o static/css/tailwind-prebuilt.css --content 'templates/**/*.html' --minify
	@echo "✅ Tailwind CSS built: static/css/tailwind-prebuilt.css"

# Quality
lint:
	ruff check .

format:
	ruff format .
	ruff check --fix .

test:
	pytest

test-cov:
	pytest --cov=. --cov-report=html
	@echo "Coverage report: htmlcov/index.html"

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .ruff_cache 2>/dev/null || true

# Full development setup
setup: dev docker-up migrate static
	@echo ""
	@echo "✅ Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Copy .env.example to .env and configure"
	@echo "  2. Run: make superuser"
	@echo "  3. Run: make run"
	@echo ""
