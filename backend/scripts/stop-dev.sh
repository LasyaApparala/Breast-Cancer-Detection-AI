#!/bin/bash

# BreastGuard AI - Development Stop Script
# Stops all development services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
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

# Stop service from PID file
stop_service() {
    local service_name=$1
    local pid_file="$LOG_DIR/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "Stopping $service_name (PID: $pid)..."
            kill "$pid"
            
            # Wait for process to stop
            local count=0
            while kill -0 "$pid" 2>/dev/null && [ $count -lt 10 ]; do
                sleep 1
                count=$((count + 1))
            done
            
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                log_warning "Force killing $service_name..."
                kill -9 "$pid"
            fi
            
            log_success "$service_name stopped"
        else
            log_warning "$service_name PID file exists but process not running"
        fi
        
        rm -f "$pid_file"
    else
        log_info "$service_name PID file not found"
    fi
}

# Stop services by process name
stop_by_name() {
    local pattern=$1
    local service_name=$2
    
    local pids=$(pgrep -f "$pattern" 2>/dev/null || true)
    
    if [ -n "$pids" ]; then
        log_info "Stopping $service_name processes..."
        echo "$pids" | xargs kill 2>/dev/null || true
        
        # Wait for processes to stop
        local count=0
        while pgrep -f "$pattern" > /dev/null 2>&1 && [ $count -lt 10 ]; do
            sleep 1
            count=$((count + 1))
        done
        
        # Force kill if still running
        local remaining_pids=$(pgrep -f "$pattern" 2>/dev/null || true)
        if [ -n "$remaining_pids" ]; then
            log_warning "Force killing $service_name processes..."
            echo "$remaining_pids" | xargs kill -9 2>/dev/null || true
        fi
        
        log_success "$service_name processes stopped"
    else
        log_info "No $service_name processes found"
    fi
}

# Stop database services
stop_databases() {
    log_info "Stopping database services..."
    
    # Stop PostgreSQL
    if command -v pg_ctl &> /dev/null; then
        pg_ctl -D /usr/local/var/postgres stop 2>/dev/null || true
        log_info "PostgreSQL stopped"
    fi
    
    # Stop Redis
    if command -v redis-cli &> /dev/null; then
        redis-cli shutdown 2>/dev/null || true
        log_info "Redis stopped"
    fi
    
    # Stop MongoDB
    if command -v mongod &> /dev/null; then
        pkill -f "mongod" 2>/dev/null || true
        log_info "MongoDB stopped"
    fi
    
    log_success "Database services stopped"
}

# Clean up temporary files
cleanup_temp_files() {
    log_info "Cleaning up temporary files..."
    
    # Remove PID files
    rm -f "$LOG_DIR"/*.pid
    
    # Remove temporary files
    rm -rf "$PROJECT_ROOT/tmp" 2>/dev/null || true
    rm -rf "$PROJECT_ROOT/__pycache__" 2>/dev/null || true
    find "$PROJECT_ROOT" -name "*.pyc" -delete 2>/dev/null || true
    find "$PROJECT_ROOT" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    log_success "Temporary files cleaned up"
}

# Show final status
show_final_status() {
    echo
    echo "🛑 BreastGuard AI Development Environment Stopped"
    echo
    echo "All services have been stopped."
    echo "Logs are preserved in: $LOG_DIR"
    echo
    echo "To restart development environment:"
    echo "  ./scripts/start-dev.sh"
    echo
}

# Main function
main() {
    log_info "Stopping BreastGuard AI development environment..."
    
    # Stop individual services
    stop_service "backend"
    stop_service "ml_service"
    stop_service "document_parser"
    stop_service "frontend"
    stop_service "celery"
    
    # Stop any remaining processes
    stop_by_name "uvicorn.*main:app" "Backend/ML/Parser Services"
    stop_by_name "celery.*worker" "Celery Workers"
    stop_by_name "npm.*run.*dev" "Frontend Development"
    
    # Stop database services (optional - comment out if you want databases to keep running)
    if [ "$1" != "--keep-databases" ]; then
        stop_databases
    else
        log_info "Keeping database services running (--keep-databases flag used)"
    fi
    
    # Clean up
    cleanup_temp_files
    
    # Show final status
    show_final_status
}

# Run main function
main "$@"
