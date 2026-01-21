#!/bin/bash
#
# CSU Tracker - Development Server Script
# Starts all services: Docker, Django, Celery Worker, Celery Beat
#
# Usage: ./scripts/dev.sh [command]
#   start   - Start all services (default)
#   stop    - Stop all services
#   restart - Restart all services
#   logs    - Show logs from all services
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# PID file locations
PID_DIR="$PROJECT_DIR/.pids"
DJANGO_PID="$PID_DIR/django.pid"
CELERY_WORKER_PID="$PID_DIR/celery_worker.pid"
CELERY_BEAT_PID="$PID_DIR/celery_beat.pid"

# Log file locations
LOG_DIR="$PROJECT_DIR/.logs"
DJANGO_LOG="$LOG_DIR/django.log"
CELERY_WORKER_LOG="$LOG_DIR/celery_worker.log"
CELERY_BEAT_LOG="$LOG_DIR/celery_beat.log"

# Create directories
mkdir -p "$PID_DIR" "$LOG_DIR"

print_status() {
    echo -e "${BLUE}[CSU Tracker]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

check_venv() {
    if [[ -z "$VIRTUAL_ENV" ]]; then
        if [[ -f "$PROJECT_DIR/.venv/bin/activate" ]]; then
            print_status "Activating virtual environment..."
            source "$PROJECT_DIR/.venv/bin/activate"
        else
            print_error "Virtual environment not found. Please create one first:"
            echo "  python3.12 -m venv .venv"
            echo "  source .venv/bin/activate"
            echo "  pip install -e ."
            exit 1
        fi
    fi
}

check_env() {
    if [[ ! -f "$PROJECT_DIR/.env" ]]; then
        print_warning ".env file not found. Creating from template..."
        cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
        print_warning "Please edit .env and set your SECRET_KEY and VAPID keys"
    fi
}

start_docker() {
    print_status "Starting Docker services (PostgreSQL + Redis)..."
    docker-compose up -d
    
    # Wait for services to be healthy
    print_status "Waiting for database to be ready..."
    for i in {1..30}; do
        if docker-compose exec -T db pg_isready -U csu_user -d csu_tracker >/dev/null 2>&1; then
            print_success "Database is ready"
            break
        fi
        if [[ $i -eq 30 ]]; then
            print_error "Database failed to start"
            exit 1
        fi
        sleep 1
    done
}

stop_docker() {
    print_status "Stopping Docker services..."
    docker-compose down
}

run_migrations() {
    print_status "Running database migrations..."
    python manage.py migrate --no-input
    print_success "Migrations complete"
}

start_django() {
    if [[ -f "$DJANGO_PID" ]] && kill -0 $(cat "$DJANGO_PID") 2>/dev/null; then
        print_warning "Django server already running (PID: $(cat $DJANGO_PID))"
        return
    fi
    
    print_status "Starting Django development server..."
    python manage.py runserver 0.0.0.0:8000 > "$DJANGO_LOG" 2>&1 &
    echo $! > "$DJANGO_PID"
    print_success "Django server started (PID: $(cat $DJANGO_PID))"
}

start_celery_worker() {
    if [[ -f "$CELERY_WORKER_PID" ]] && kill -0 $(cat "$CELERY_WORKER_PID") 2>/dev/null; then
        print_warning "Celery worker already running (PID: $(cat $CELERY_WORKER_PID))"
        return
    fi
    
    print_status "Starting Celery worker..."
    celery -A core worker -l INFO > "$CELERY_WORKER_LOG" 2>&1 &
    echo $! > "$CELERY_WORKER_PID"
    print_success "Celery worker started (PID: $(cat $CELERY_WORKER_PID))"
}

start_celery_beat() {
    if [[ -f "$CELERY_BEAT_PID" ]] && kill -0 $(cat "$CELERY_BEAT_PID") 2>/dev/null; then
        print_warning "Celery beat already running (PID: $(cat $CELERY_BEAT_PID))"
        return
    fi
    
    print_status "Starting Celery beat scheduler..."
    celery -A core beat -l INFO > "$CELERY_BEAT_LOG" 2>&1 &
    echo $! > "$CELERY_BEAT_PID"
    print_success "Celery beat started (PID: $(cat $CELERY_BEAT_PID))"
}

stop_process() {
    local pid_file=$1
    local name=$2
    
    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            print_status "Stopping $name (PID: $pid)..."
            kill "$pid" 2>/dev/null || true
            sleep 1
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid" 2>/dev/null || true
            fi
            print_success "$name stopped"
        fi
        rm -f "$pid_file"
    fi
}

stop_services() {
    stop_process "$CELERY_BEAT_PID" "Celery beat"
    stop_process "$CELERY_WORKER_PID" "Celery worker"
    stop_process "$DJANGO_PID" "Django server"
}

show_logs() {
    echo ""
    echo "====== Django Server ======"
    tail -50 "$DJANGO_LOG" 2>/dev/null || echo "No logs yet"
    echo ""
    echo "====== Celery Worker ======"
    tail -30 "$CELERY_WORKER_LOG" 2>/dev/null || echo "No logs yet"
    echo ""
    echo "====== Celery Beat ======"
    tail -20 "$CELERY_BEAT_LOG" 2>/dev/null || echo "No logs yet"
}

show_status() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}       CSU Tracker - Service Status     ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo ""
    
    # Docker services
    if docker-compose ps --services --filter "status=running" 2>/dev/null | grep -q .; then
        print_success "Docker services: Running"
    else
        print_error "Docker services: Stopped"
    fi
    
    # Django
    if [[ -f "$DJANGO_PID" ]] && kill -0 $(cat "$DJANGO_PID") 2>/dev/null; then
        print_success "Django server: Running (PID: $(cat $DJANGO_PID))"
    else
        print_error "Django server: Stopped"
    fi
    
    # Celery Worker
    if [[ -f "$CELERY_WORKER_PID" ]] && kill -0 $(cat "$CELERY_WORKER_PID") 2>/dev/null; then
        print_success "Celery worker: Running (PID: $(cat $CELERY_WORKER_PID))"
    else
        print_error "Celery worker: Stopped"
    fi
    
    # Celery Beat
    if [[ -f "$CELERY_BEAT_PID" ]] && kill -0 $(cat "$CELERY_BEAT_PID") 2>/dev/null; then
        print_success "Celery beat: Running (PID: $(cat $CELERY_BEAT_PID))"
    else
        print_error "Celery beat: Stopped"
    fi
    
    echo ""
}

start_all() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}       CSU Tracker - Starting Up        ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo ""
    
    check_venv
    check_env
    start_docker
    run_migrations
    start_django
    start_celery_worker
    start_celery_beat
    
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════${NC}"
    echo -e "${GREEN}         All Services Started!          ${NC}"
    echo -e "${GREEN}═══════════════════════════════════════${NC}"
    echo ""
    echo "  🌐 Web App:  http://localhost:8000"
    echo "  🔧 Admin:    http://localhost:8000/admin"
    echo ""
    echo "  📋 View logs:    ./scripts/dev.sh logs"
    echo "  🛑 Stop all:     ./scripts/dev.sh stop"
    echo "  📊 Status:       ./scripts/dev.sh status"
    echo ""
}

stop_all() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}      CSU Tracker - Shutting Down       ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo ""
    
    stop_services
    stop_docker
    
    echo ""
    print_success "All services stopped"
    echo ""
}

# Handle Ctrl+C gracefully
trap 'echo ""; print_warning "Interrupted! Stopping services..."; stop_services; exit 0' INT TERM

# Main command handling
case "${1:-start}" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    restart)
        stop_all
        sleep 2
        start_all
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|logs|status}"
        exit 1
        ;;
esac
