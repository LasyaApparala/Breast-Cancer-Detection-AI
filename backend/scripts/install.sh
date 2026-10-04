#!/bin/bash

# BreastGuard AI - Native Installation Script
# Supports Ubuntu 20.04+, CentOS 8+, and macOS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/breastguard-ai"
SERVICE_USER="breastguard"
PYTHON_VERSION="3.11"

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

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            OS=$NAME
            VER=$VERSION_ID
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macOS"
        VER=$(sw_vers -productVersion)
    else
        log_error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
    
    log_info "Detected OS: $OS $VER"
}

# Check system requirements
check_requirements() {
    log_info "Checking system requirements..."
    
    # Check memory
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        MEMORY=$(free -m | awk 'NR==2{printf "%.0f", $2/1024}')
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        MEMORY=$(sysctl -n hw.memsize | awk '{printf "%.0f", $1/1024/1024/1024}')
    fi
    
    if [ "$MEMORY" -lt 16 ]; then
        log_warning "System has ${MEMORY}GB RAM. 16GB+ recommended for production."
    fi
    
    # Check disk space
    DISK_SPACE=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$DISK_SPACE" -lt 10 ]; then
        log_error "Insufficient disk space. At least 10GB required."
        exit 1
    fi
    
    log_success "System requirements check passed"
}

# Install system dependencies
install_system_deps() {
    log_info "Installing system dependencies..."
    
    if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
        sudo apt-get update
        sudo apt-get install -y \
            python3.11 \
            python3.11-venv \
            python3.11-dev \
            python3-pip \
            postgresql \
            postgresql-contrib \
            redis-server \
            mongodb \
            nginx \
            curl \
            wget \
            git \
            build-essential \
            pkg-config \
            libpq-dev \
            libssl-dev \
            libffi-dev \
            libjpeg-dev \
            libpng-dev \
            libtiff-dev \
            libwebp-dev \
            zlib1g-dev \
            libfreetype6-dev \
            liblcms2-dev \
            libopenjp2-7-dev \
            libtk8.6 \
            tesseract-ocr \
            tesseract-ocr-eng \
            libtesseract-dev \
            nodejs \
            npm
            
    elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
        sudo yum update -y
        sudo yum install -y \
            python3.11 \
            python3.11-pip \
            python3.11-devel \
            postgresql-server \
            postgresql-contrib \
            redis \
            mongodb \
            nginx \
            curl \
            wget \
            git \
            gcc \
            gcc-c++ \
            make \
            pkgconfig \
            libpq-devel \
            openssl-devel \
            libffi-devel \
            libjpeg-turbo-devel \
            libpng-devel \
            libtiff-devel \
            libwebp-devel \
            zlib-devel \
            freetype-devel \
            lcms2-devel \
            openjpeg2-devel \
            tk-devel \
            tesseract \
            tesseract-langpack-eng \
            nodejs \
            npm
            
    elif [[ "$OS" == "macOS" ]]; then
        # Install Homebrew if not present
        if ! command -v brew &> /dev/null; then
            log_info "Installing Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        
        brew update
        brew install \
            python@3.11 \
            postgresql@15 \
            redis \
            mongodb/brew/mongodb-community \
            nginx \
            curl \
            wget \
            git \
            pkg-config \
            libpq \
            openssl \
            libffi \
            jpeg \
            libpng \
            libtiff \
            webp \
            zlib \
            freetype \
            little-cms2 \
            openjpeg \
            tesseract \
            tesseract-lang \
            node
    fi
    
    log_success "System dependencies installed"
}

# Create service user
create_service_user() {
    log_info "Creating service user..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if ! id "$SERVICE_USER" &>/dev/null; then
            sudo useradd -r -s /bin/false -d $INSTALL_DIR $SERVICE_USER
            log_success "Service user created"
        else
            log_warning "Service user already exists"
        fi
    fi
}

# Install Python dependencies
install_python_deps() {
    log_info "Installing Python dependencies..."
    
    # Create virtual environment
    sudo -u $SERVICE_USER python3.11 -m venv $INSTALL_DIR/venv
    sudo -u $SERVICE_USER $INSTALL_DIR/venv/bin/pip install --upgrade pip
    
    # Install backend dependencies
    sudo -u $SERVICE_USER $INSTALL_DIR/venv/bin/pip install -r $INSTALL_DIR/backend/requirements.txt
    
    # Install ML service dependencies
    sudo -u $SERVICE_USER $INSTALL_DIR/venv/bin/pip install -r $INSTALL_DIR/ml_service/requirements.txt
    
    # Install document parser dependencies
    sudo -u $SERVICE_USER $INSTALL_DIR/venv/bin/pip install -r $INSTALL_DIR/document_parser/requirements.txt
    
    log_success "Python dependencies installed"
}

# Install Node.js dependencies
install_node_deps() {
    log_info "Installing Node.js dependencies..."
    
    cd $INSTALL_DIR/frontend
    sudo -u $SERVICE_USER npm install
    
    log_success "Node.js dependencies installed"
}

# Setup databases
setup_databases() {
    log_info "Setting up databases..."
    
    # PostgreSQL setup
    if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
        sudo systemctl start postgresql
        sudo systemctl enable postgresql
        
        # Create database and user
        sudo -u postgres psql -c "CREATE DATABASE breastguard_ai;"
        sudo -u postgres psql -c "CREATE USER breastguard_user WITH PASSWORD 'secure_password';"
        sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE breastguard_ai TO breastguard_user;"
        
    elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
        sudo postgresql-setup initdb
        sudo systemctl start postgresql
        sudo systemctl enable postgresql
        
        sudo -u postgres psql -c "CREATE DATABASE breastguard_ai;"
        sudo -u postgres psql -c "CREATE USER breastguard_user WITH PASSWORD 'secure_password';"
        sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE breastguard_ai TO breastguard_user;"
        
    elif [[ "$OS" == "macOS" ]]; then
        brew services start postgresql@15
        createdb breastguard_ai
        createuser breastguard_user
        psql -d breastguard_ai -c "ALTER USER breastguard_user WITH PASSWORD 'secure_password';"
    fi
    
    # Redis setup
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo systemctl start redis
        sudo systemctl enable redis
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew services start redis
    fi
    
    # MongoDB setup
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo systemctl start mongod
        sudo systemctl enable mongod
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew services start mongodb/brew/mongodb-community
    fi
    
    log_success "Databases setup completed"
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    cd $INSTALL_DIR/backend
    sudo -u $SERVICE_USER $INSTALL_DIR/venv/bin/alembic upgrade head
    
    log_success "Database migrations completed"
}

# Create configuration files
create_configs() {
    log_info "Creating configuration files..."
    
    # Environment file
    cat > $INSTALL_DIR/.env << EOF
# BreastGuard AI Configuration
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=breastguard_ai
POSTGRES_USER=breastguard_user
POSTGRES_PASSWORD=secure_password

# MongoDB
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=breastguard_ai_docs

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
JWT_PRIVATE_KEY_PATH=$INSTALL_DIR/keys/private.pem
JWT_PUBLIC_KEY_PATH=$INSTALL_DIR/keys/public.pem

# Storage
UPLOAD_DIR=$INSTALL_DIR/uploads
MODEL_DIR=$INSTALL_DIR/models

# Services
ML_SERVICE_HOST=localhost
ML_SERVICE_PORT=8001
DOCUMENT_PARSER_HOST=localhost
DOCUMENT_PARSER_PORT=8002
EOF

    # SSL keys
    mkdir -p $INSTALL_DIR/keys
    openssl genrsa -out $INSTALL_DIR/keys/private.pem 2048
    openssl rsa -in $INSTALL_DIR/keys/private.pem -pubout -out $INSTALL_DIR/keys/public.pem
    
    # Set permissions
    chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR
    chmod 600 $INSTALL_DIR/keys/private.pem
    chmod 644 $INSTALL_DIR/keys/public.pem
    
    log_success "Configuration files created"
}

# Create systemd services
create_systemd_services() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        log_info "Creating systemd services..."
        
        # Backend service
        cat > /etc/systemd/system/breastguard-backend.service << EOF
[Unit]
Description=BreastGuard AI Backend
After=network.target postgresql.service redis.service mongod.service

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR/backend
Environment=PATH=$INSTALL_DIR/venv/bin
ExecStart=$INSTALL_DIR/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

        # ML Service
        cat > /etc/systemd/system/breastguard-ml.service << EOF
[Unit]
Description=BreastGuard AI ML Service
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR/ml_service
Environment=PATH=$INSTALL_DIR/venv/bin
ExecStart=$INSTALL_DIR/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

        # Document Parser Service
        cat > /etc/systemd/system/breastguard-parser.service << EOF
[Unit]
Description=BreastGuard AI Document Parser
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR/document_parser
Environment=PATH=$INSTALL_DIR/venv/bin
ExecStart=$INSTALL_DIR/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8002
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

        # Celery Worker
        cat > /etc/systemd/system/breastguard-celery.service << EOF
[Unit]
Description=BreastGuard AI Celery Worker
After=network.target redis.service

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR/backend
Environment=PATH=$INSTALL_DIR/venv/bin
ExecStart=$INSTALL_DIR/venv/bin/celery -A backend.celery worker --loglevel=info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

        # Reload systemd and enable services
        sudo systemctl daemon-reload
        sudo systemctl enable breastguard-backend
        sudo systemctl enable breastguard-ml
        sudo systemctl enable breastguard-parser
        sudo systemctl enable breastguard-celery
        
        log_success "Systemd services created"
    fi
}

# Setup Nginx
setup_nginx() {
    log_info "Setting up Nginx..."
    
    cat > /etc/nginx/sites-available/breastguard << EOF
server {
    listen 80;
    server_name localhost;
    
    # Frontend
    location / {
        root $INSTALL_DIR/frontend/dist;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }
    
    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # ML Service
    location /ml/ {
        proxy_pass http://localhost:8001/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Document Parser
    location /parser/ {
        proxy_pass http://localhost:8002/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

    # Enable site
    sudo ln -sf /etc/nginx/sites-available/breastguard /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Test and restart nginx
    sudo nginx -t
    sudo systemctl restart nginx
    sudo systemctl enable nginx
    
    log_success "Nginx configured"
}

# Build frontend
build_frontend() {
    log_info "Building frontend..."
    
    cd $INSTALL_DIR/frontend
    sudo -u $SERVICE_USER npm run build
    
    log_success "Frontend built"
}

# Start services
start_services() {
    log_info "Starting services..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo systemctl start breastguard-backend
        sudo systemctl start breastguard-ml
        sudo systemctl start breastguard-parser
        sudo systemctl start breastguard-celery
        
        # Wait for services to start
        sleep 10
        
        # Check service status
        for service in breastguard-backend breastguard-ml breastguard-parser breastguard-celery; do
            if sudo systemctl is-active --quiet $service; then
                log_success "$service is running"
            else
                log_error "$service failed to start"
                sudo systemctl status $service
            fi
        done
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # Start services manually on macOS
        cd $INSTALL_DIR/backend
        sudo -u $SERVICE_USER $INSTALL_DIR/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000 &
        
        cd $INSTALL_DIR/ml_service
        sudo -u $SERVICE_USER $INSTALL_DIR/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8001 &
        
        cd $INSTALL_DIR/document_parser
        sudo -u $SERVICE_USER $INSTALL_DIR/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8002 &
        
        log_success "Services started (macOS)"
    fi
}

# Create admin user
create_admin_user() {
    log_info "Creating admin user..."
    
    cd $INSTALL_DIR/backend
    sudo -u $SERVICE_USER $INSTALL_DIR/venv/bin/python -c "
from backend.security.auth import hash_password
from backend.models.user import User
from backend.db import SessionLocal

db = SessionLocal()
try:
    admin_user = User(
        email='admin@breastguard.ai',
        name='System Administrator',
        role='admin',
        password_hash=hash_password('admin123')
    )
    db.add(admin_user)
    db.commit()
    print('Admin user created successfully')
    print('Email: admin@breastguard.ai')
    print('Password: admin123')
except Exception as e:
    print(f'Error creating admin user: {e}')
finally:
    db.close()
"
    
    log_success "Admin user created"
}

# Main installation function
main() {
    log_info "Starting BreastGuard AI native installation..."
    
    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
    
    detect_os
    check_requirements
    
    # Create installation directory
    mkdir -p $INSTALL_DIR
    chown $SERVICE_USER:$SERVICE_USER $INSTALL_DIR 2>/dev/null || true
    
    # Copy source files
    log_info "Copying source files..."
    cp -r . $INSTALL_DIR/
    chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR
    
    install_system_deps
    create_service_user
    install_python_deps
    install_node_deps
    setup_databases
    create_configs
    run_migrations
    build_frontend
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        create_systemd_services
        setup_nginx
    fi
    
    start_services
    create_admin_user
    
    log_success "BreastGuard AI installation completed!"
    echo
    echo "🎉 Installation Complete!"
    echo
    echo "Access the application at:"
    echo "  Frontend: http://localhost"
    echo "  API: http://localhost/api/v1"
    echo "  Admin: admin@breastguard.ai / admin123"
    echo
    echo "Service management:"
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "  Start: sudo systemctl start breastguard-backend"
        echo "  Stop: sudo systemctl stop breastguard-backend"
        echo "  Status: sudo systemctl status breastguard-backend"
    else
        echo "  Services are running in background processes"
    fi
    echo
    echo "Configuration file: $INSTALL_DIR/.env"
    echo "Logs: $INSTALL_DIR/logs/"
    echo
}

# Run main function
main "$@"
