#!/bin/bash
#
# CSU Tracker - Initial Setup Script
# Run this once to set up the project from scratch
#

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo ""
echo "═══════════════════════════════════════"
echo "     CSU Tracker - Initial Setup       "
echo "═══════════════════════════════════════"
echo ""

# Check Python version
echo "Checking Python version..."
if ! command -v python3.12 &> /dev/null; then
    echo "❌ Python 3.12 is required but not found."
    echo "   Install with: brew install python@3.12"
    exit 1
fi
echo "✓ Python 3.12 found"

# Check Docker
echo "Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is required but not found."
    echo "   Install Docker Desktop from: https://docker.com"
    exit 1
fi
echo "✓ Docker found"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [[ ! -d ".venv" ]]; then
    python3.12 -m venv .venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate and install
echo ""
echo "Installing dependencies..."
source .venv/bin/activate
pip install --upgrade pip -q
pip install -e ".[dev]" -q
echo "✓ Dependencies installed"

# Create .env if needed
echo ""
if [[ ! -f ".env" ]]; then
    echo "Creating .env file..."
    cp .env.example .env
    
    # Generate secret key
    SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
    
    # Update .env with secret key (macOS compatible sed)
    sed -i '' "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
    
    echo "✓ .env file created with secure SECRET_KEY"
    echo ""
    echo "⚠️  Note: You still need to generate VAPID keys for push notifications."
    echo "   Run: python -c \"from py_vapid import Vapid; v=Vapid(); v.generate_keys(); print('Private:', v.private_pem().decode()); print('Public:', v.public_key)\""
else
    echo "✓ .env file already exists"
fi

# Generate icons (optional, requires extra deps)
echo ""
echo "Checking icon generation dependencies..."
if pip show cairosvg pillow &> /dev/null; then
    echo "Generating PWA icons..."
    python generate_icons.py 2>/dev/null || echo "⚠️  Icon generation skipped (optional)"
else
    echo "⚠️  Icon generation skipped (install cairosvg pillow to generate)"
fi

# Start Docker services
echo ""
echo "Starting Docker services..."
docker-compose up -d
echo "Waiting for database..."
sleep 5

# Run migrations
echo ""
echo "Running database migrations..."
python manage.py migrate --no-input
echo "✓ Database migrations complete"

# Collect static files
echo ""
echo "Collecting static files..."
python manage.py collectstatic --no-input -q
echo "✓ Static files collected"

echo ""
echo "═══════════════════════════════════════"
echo "         Setup Complete! 🎉            "
echo "═══════════════════════════════════════"
echo ""
echo "Next steps:"
echo ""
echo "  1. Create a superuser:"
echo "     source .venv/bin/activate"
echo "     python manage.py createsuperuser"
echo ""
echo "  2. Start all services:"
echo "     ./scripts/dev.sh start"
echo ""
echo "  3. Open in browser:"
echo "     http://localhost:8000"
echo ""
