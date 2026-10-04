#!/bin/bash

# BreastGuard AI - Development Startup Script
# Runs all services in development mode without Docker

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PATH="$PROJECT_ROOT/venv"
LOG_DIR="$PROJECT_ROOT/logs"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        exit 1
    fi
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        log_error "Node.js is not installed"
        exit 1
    fi
    
    # Check PostgreSQL
    if ! command -v psql &> /dev/null; then
        log_warning "PostgreSQL is not installed. Using SQLite for development."
        export DATABASE_URL="sqlite:///./breastguard_dev.db"
    fi
    
    # Check Redis
    if ! command -v redis-server &> /dev/null; then
        log_warning "Redis is not installed. Some features may not work."
    fi
    
    # Check MongoDB
    if ! command -v mongod &> /dev/null; then
        log_warning "MongoDB is not installed. Document storage will be disabled."
    fi
    
    log_success "Prerequisites check completed"
}

# Setup virtual environment
setup_venv() {
    log_info "Setting up Python virtual environment..."
    
    if [ ! -d "$VENV_PATH" ]; then
        python3 -m venv "$VENV_PATH"
        log_success "Virtual environment created"
    else
        log_info "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source "$VENV_PATH/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies
    log_info "Installing Python dependencies..."
    pip install -r "$PROJECT_ROOT/backend/requirements.txt"
    pip install -r "$PROJECT_ROOT/ml_service/requirements.txt"
    pip install -r "$PROJECT_ROOT/document_parser/requirements.txt"
    
    log_success "Python dependencies installed"
}

# Setup Node.js dependencies
setup_node_deps() {
    log_info "Setting up Node.js dependencies..."
    
    cd "$PROJECT_ROOT/frontend"
    
    if [ ! -d "node_modules" ]; then
        npm install
        log_success "Node.js dependencies installed"
    else
        log_info "Node.js dependencies already exist"
    fi
    
    cd "$PROJECT_ROOT"
}

# Setup databases
setup_databases() {
    log_info "Setting up databases..."
    
    # Create logs directory
    mkdir -p "$LOG_DIR"
    
    # Start PostgreSQL if available
    if command -v pg_ctl &> /dev/null; then
        pg_ctl -D /usr/local/var/postgres start 2>/dev/null || true
        log_info "PostgreSQL started"
    fi
    
    # Start Redis if available
    if command -v redis-server &> /dev/null; then
        redis-server --daemonize yes --port 6379 2>/dev/null || true
        log_info "Redis started"
    fi
    
    # Start MongoDB if available
    if command -v mongod &> /dev/null; then
        mongod --dbpath "$PROJECT_ROOT/data/mongodb" --fork --logpath "$LOG_DIR/mongodb.log" 2>/dev/null || true
        log_info "MongoDB started"
    fi
    
    # Run database migrations
    cd "$PROJECT_ROOT/backend"
    export PYTHONPATH="$PROJECT_ROOT/backend:$PYTHONPATH"
    
    if [ -f "alembic.ini" ]; then
        alembic upgrade head
        log_success "Database migrations completed"
    fi
    
    cd "$PROJECT_ROOT"
}

# Start backend service
start_backend() {
    log_info "Starting backend service..."
    
    cd "$PROJECT_ROOT/backend"
    export PYTHONPATH="$PROJECT_ROOT/backend:$PYTHONPATH"
    export DATABASE_URL="${DATABASE_URL:-postgresql://breastguard_user:secure_password@localhost:5432/breastguard_ai}"
    export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
    export MONGODB_URL="${MONGODB_URL:-mongodb://localhost:27017}"
    export JWT_PRIVATE_KEY_PATH="$PROJECT_ROOT/keys/private.pem"
    export JWT_PUBLIC_KEY_PATH="$PROJECT_ROOT/keys/public.pem"
    
    # Create SSL keys if they don't exist
    mkdir -p "$PROJECT_ROOT/keys"
    if [ ! -f "$PROJECT_ROOT/keys/private.pem" ]; then
        openssl genrsa -out "$PROJECT_ROOT/keys/private.pem" 2048
        openssl rsa -in "$PROJECT_ROOT/keys/private.pem" -pubout -out "$PROJECT_ROOT/keys/public.pem"
        log_info "SSL keys generated"
    fi
    
    # Start backend in background
    python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload > "$LOG_DIR/backend.log" 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > "$LOG_DIR/backend.pid"
    
    log_success "Backend service started (PID: $BACKEND_PID)"
}

# Start ML service
start_ml_service() {
    log_info "Starting ML service..."
    
    cd "$PROJECT_ROOT/ml_service"
    export PYTHONPATH="$PROJECT_ROOT/ml_service:$PYTHONPATH"
    export MODEL_PATH="$PROJECT_ROOT/models"
    
    # Start ML service in background
    python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload > "$LOG_DIR/ml_service.log" 2>&1 &
    ML_PID=$!
    echo $ML_PID > "$LOG_DIR/ml_service.pid"
    
    log_success "ML service started (PID: $ML_PID)"
}

# Start document parser service
start_document_parser() {
    log_info "Starting document parser service..."
    
    cd "$PROJECT_ROOT/document_parser"
    export PYTHONPATH="$PROJECT_ROOT/document_parser:$PYTHONPATH"
    export TESSERACT_PATH="${TESSERACT_PATH:-/usr/bin/tesseract}"
    
    # Start document parser in background
    python -m uvicorn main:app --host 0.0.0.0 --port 8002 --reload > "$LOG_DIR/document_parser.log" 2>&1 &
    PARSER_PID=$!
    echo $PARSER_PID > "$LOG_DIR/document_parser.pid"
    
    log_success "Document parser service started (PID: $PARSER_PID)"
}

# Start frontend
start_frontend() {
    log_info "Starting frontend..."
    
    cd "$PROJECT_ROOT/frontend"
    
    # Start frontend in background
    npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > "$LOG_DIR/frontend.pid"
    
    log_success "Frontend started (PID: $FRONTEND_PID)"
}

# Start Celery worker
start_celery() {
    log_info "Starting Celery worker..."
    
    cd "$PROJECT_ROOT/backend"
    export PYTHONPATH="$PROJECT_ROOT/backend:$PYTHONPATH"
    
    # Start Celery worker in background
    celery -A backend.celery worker --loglevel=info > "$LOG_DIR/celery.log" 2>&1 &
    CELERY_PID=$!
    echo $CELERY_PID > "$LOG_DIR/celery.pid"
    
    log_success "Celery worker started (PID: $CELERY_PID)"
}

# Wait for services to be ready
wait_for_services() {
    log_info "Waiting for services to be ready..."
    
    # Wait for backend
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            log_success "Backend service is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "Backend service failed to start"
            return 1
        fi
        sleep 2
    done
    
    # Wait for ML service
    for i in {1..30}; do
        if curl -s http://localhost:8001/health > /dev/null 2>&1; then
            log_success "ML service is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "ML service failed to start"
            return 1
        fi
        sleep 2
    done
    
    # Wait for document parser
    for i in {1..30}; do
        if curl -s http://localhost:8002/health > /dev/null 2>&1; then
            log_success "Document parser service is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "Document parser service failed to start"
            return 1
        fi
        sleep 2
    done
    
    # Wait for frontend
    for i in {1..30}; do
        if curl -s http://localhost:3000 > /dev/null 2>&1; then
            log_success "Frontend is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "Frontend failed to start"
            return 1
        fi
        sleep 2
    done
}

# Show status
show_status() {
    echo
    echo "🎉 BreastGuard AI Development Environment Started!"
    echo
    echo "Services:"
    echo "  Frontend:     http://localhost:3000"
    echo "  Backend API:  http://localhost:8000"
    echo "  ML Service:   http://localhost:8001"
    echo "  Document Parser: http://localhost:8002"
    echo "  API Docs:     http://localhost:8000/docs"
    echo
    echo "Logs:"
    echo "  Backend:       tail -f $LOG_DIR/backend.log"
    echo "  ML Service:    tail -f $LOG_DIR/ml_service.log"
    echo "  Document Parser: tail -f $LOG_DIR/document_parser.log"
    echo "  Frontend:      tail -f $LOG_DIR/frontend.log"
    echo "  Celery:        tail -f $LOG_DIR/celery.log"
    echo
    echo "Stop all services:"
    echo "  ./scripts/stop-dev.sh"
    echo
    echo "Create admin user:"
    echo "  cd backend && python -c \"from backend.security.auth import hash_password; from backend.models.user import User; from backend.db import SessionLocal; db=SessionLocal(); admin=User(email='admin@breastguard.ai', name='Admin', role='admin', password_hash=hash_password('admin123')); db.add(admin); db.commit(); print('Admin user created')\""
    echo
}

# Cleanup function
cleanup() {
    log_info "Shutting down services..."
    
    # Kill all background processes
    if [ -f "$LOG_DIR/backend.pid" ]; then
        kill $(cat "$LOG_DIR/backend.pid") 2>/dev/null || true
        rm "$LOG_DIR/backend.pid"
    fi
    
    if [ -f "$LOG_DIR/ml_service.pid" ]; then
        kill $(cat "$LOG_DIR/ml_service.pid") 2>/dev/null || true
        rm "$LOG_DIR/ml_service.pid"
    fi
    
    if [ -f "$LOG_DIR/document_parser.pid" ]; then
        kill $(cat "$LOG_DIR/document_parser.pid") 2>/dev/null || true
        rm "$LOG_DIR/document_parser.pid"
    fi
    
    if [ -f "$LOG_DIR/frontend.pid" ]; then
        kill $(cat "$LOG_DIR/frontend.pid") 2>/dev/null || true
        rm "$LOG_DIR/frontend.pid"
    fi
    
    if [ -f "$LOG_DIR/celery.pid" ]; then
        kill $(cat "$LOG_DIR/celery.pid") 2>/dev/null || true
        rm "$LOG_DIR/celery.pid"
    fi
    
    # Kill any remaining processes
    pkill -f "uvicorn.*main:app" 2>/dev/null || true
    pkill -f "celery.*worker" 2>/dev/null || true
    pkill -f "npm.*run.*dev" 2>/dev/null || true
    
    log_success "All services stopped"
}

# Set up signal handlers
trap cleanup EXIT INT TERM

# Main function
main() {
    log_info "Starting BreastGuard AI development environment..."
    
    check_prerequisites
    setup_venv
    setup_node_deps
    setup_databases
    
    # Start all services
    start_backend
    start_ml_service
    start_document_parser
    start_celery
    start_frontend
    
    # Wait for services to be ready
    wait_for_services
    
    # Show status
    show_status
    
    # Keep script running
    log_info "Development environment is running. Press Ctrl+C to stop all services."
    
    # Wait for interrupt signal
    while true; do
        sleep 1
    done
}

# Run main function
main "$@"
