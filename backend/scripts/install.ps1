# BreastGuard AI - Windows PowerShell Installation Script
# Supports Windows 10/11 and Windows Server 2019+

param(
    [string]$InstallDir = "C:\breastguard-ai",
    [string]$ServiceUser = "breastguard",
    [switch]$SkipDeps,
    [switch]$SkipServices
)

# Colors for output
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Log-Info($message) {
    Write-ColorOutput Cyan "[INFO] $message"
}

function Log-Success($message) {
    Write-ColorOutput Green "[SUCCESS] $message"
}

function Log-Warning($message) {
    Write-ColorOutput Yellow "[WARNING] $message"
}

function Log-Error($message) {
    Write-ColorOutput Red "[ERROR] $message"
}

# Check if running as Administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Check system requirements
function Test-SystemRequirements {
    Log-Info "Checking system requirements..."
    
    # Check memory
    $memory = Get-CimInstance -ClassName Win32_ComputerSystem | Select-Object TotalPhysicalMemory
    $memoryGB = [math]::Round($memory.TotalPhysicalMemory / 1GB, 0)
    
    if ($memoryGB -lt 16) {
        Log-Warning "System has ${memoryGB}GB RAM. 16GB+ recommended for production."
    }
    
    # Check disk space
    $disk = Get-PSDrive -Name C
    $freeSpaceGB = [math]::Round($disk.Free / 1GB, 0)
    
    if ($freeSpaceGB -lt 10) {
        Log-Error "Insufficient disk space. At least 10GB required."
        exit 1
    }
    
    Log-Success "System requirements check passed"
}

# Install Chocolatey if not present
function Install-Chocolatey {
    if (!(Get-Command choco -ErrorAction SilentlyContinue)) {
        Log-Info "Installing Chocolatey..."
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
        refreshenv
        Log-Success "Chocolatey installed"
    } else {
        Log-Info "Chocolatey already installed"
    }
}

# Install system dependencies
function Install-SystemDependencies {
    if ($SkipDeps) {
        Log-Warning "Skipping system dependencies installation"
        return
    }
    
    Log-Info "Installing system dependencies..."
    
    # Install Python
    if (!(Get-Command python -ErrorAction SilentlyContinue)) {
        choco install python311 -y
        refreshenv
    }
    
    # Install Node.js
    if (!(Get-Command node -ErrorAction SilentlyContinue)) {
        choco install nodejs -y
        refreshenv
    }
    
    # Install PostgreSQL
    if (!(Get-Command psql -ErrorAction SilentlyContinue)) {
        choco install postgresql -y --params '/Password:postgres123'
        refreshenv
    }
    
    # Install Redis
    if (!(Get-Command redis-server -ErrorAction SilentlyContinue)) {
        choco install redis-64 -y
        refreshenv
    }
    
    # Install MongoDB
    if (!(Get-Command mongod -ErrorAction SilentlyContinue)) {
        choco install mongodb -y
        refreshenv
    }
    
    # Install Nginx
    if (!(Get-Command nginx -ErrorAction SilentlyContinue)) {
        choco install nginx -y
        refreshenv
    }
    
    # Install additional tools
    choco install git -y
    choco install vcredist-all -y
    choco install visualstudio2019buildtools -y --package-parameters "--add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
    
    Log-Success "System dependencies installed"
}

# Create service user
function New-ServiceUser {
    Log-Info "Creating service user..."
    
    try {
        $user = Get-LocalUser -Name $ServiceUser -ErrorAction SilentlyContinue
        if (-not $user) {
            New-LocalUser -Name $ServiceUser -PasswordNeverExpires -Description "BreastGuard AI Service User"
            Add-LocalGroupMember -Group "Users" -Member $ServiceUser
            Log-Success "Service user created"
        } else {
            Log-Warning "Service user already exists"
        }
    } catch {
        Log-Error "Failed to create service user: $_"
        exit 1
    }
}

# Create installation directory
function Initialize-InstallationDirectory {
    Log-Info "Creating installation directory..."
    
    if (!(Test-Path $InstallDir)) {
        New-Item -ItemType Directory -Path $InstallDir -Force
    }
    
    # Set permissions
    $acl = Get-Acl $InstallDir
    $accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule($ServiceUser, "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow")
    $acl.SetAccessRule($accessRule)
    Set-Acl $InstallDir $acl
    
    Log-Success "Installation directory created"
}

# Copy source files
function Copy-SourceFiles {
    Log-Info "Copying source files..."
    
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $projectRoot = Split-Path -Parent $scriptDir
    
    Copy-Item -Path "$projectRoot\*" -Destination $InstallDir -Recurse -Force
    
    Log-Success "Source files copied"
}

# Install Python dependencies
function Install-PythonDependencies {
    Log-Info "Installing Python dependencies..."
    
    # Create virtual environment
    & python -m venv "$InstallDir\venv"
    
    # Activate virtual environment
    $venvPython = "$InstallDir\venv\Scripts\python.exe"
    $venvPip = "$InstallDir\venv\Scripts\pip.exe"
    
    # Upgrade pip
    & $venvPip install --upgrade pip
    
    # Install backend dependencies
    & $venvPip install -r "$InstallDir\backend\requirements.txt"
    
    # Install ML service dependencies
    & $venvPip install -r "$InstallDir\ml_service\requirements.txt"
    
    # Install document parser dependencies
    & $venvPip install -r "$InstallDir\document_parser\requirements.txt"
    
    Log-Success "Python dependencies installed"
}

# Install Node.js dependencies
function Install-NodeDependencies {
    Log-Info "Installing Node.js dependencies..."
    
    Set-Location $InstallDir\frontend
    npm install
    
    Log-Success "Node.js dependencies installed"
}

# Setup databases
function Initialize-Databases {
    Log-Info "Setting up databases..."
    
    # Start PostgreSQL service
    Start-Service postgresql-x64-13 -ErrorAction SilentlyContinue
    Set-Service postgresql-x64-13 -StartupType Automatic
    
    # Create database and user
    $env:PGPASSWORD = "postgres123"
    & psql -U postgres -c "CREATE DATABASE breastguard_ai;"
    & psql -U postgres -c "CREATE USER breastguard_user WITH PASSWORD 'secure_password';"
    & psql -U postgres -c "ALTER USER breastguard_user CREATEDB;"
    & psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE breastguard_ai TO breastguard_user;"
    
    # Start Redis service
    Start-Service Redis -ErrorAction SilentlyContinue
    Set-Service Redis -StartupType Automatic
    
    # Start MongoDB service
    Start-Service MongoDB -ErrorAction SilentlyContinue
    Set-Service MongoDB -StartupType Automatic
    
    Log-Success "Databases setup completed"
}

# Run database migrations
function Invoke-DatabaseMigrations {
    Log-Info "Running database migrations..."
    
    $venvPython = "$InstallDir\venv\Scripts\python.exe"
    Set-Location $InstallDir\backend
    
    & $venvPython -m alembic upgrade head
    
    Log-Success "Database migrations completed"
}

# Create configuration files
function New-ConfigurationFiles {
    Log-Info "Creating configuration files..."
    
    # Environment file
    $envContent = @"
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
JWT_PRIVATE_KEY_PATH=$InstallDir\keys\private.pem
JWT_PUBLIC_KEY_PATH=$InstallDir\keys\public.pem

# Storage
UPLOAD_DIR=$InstallDir\uploads
MODEL_DIR=$InstallDir\models

# Services
ML_SERVICE_HOST=localhost
ML_SERVICE_PORT=8001
DOCUMENT_PARSER_HOST=localhost
DOCUMENT_PARSER_PORT=8002
"@
    
    $envContent | Out-File -FilePath "$InstallDir\.env" -Encoding UTF8
    
    # Create keys directory
    New-Item -ItemType Directory -Path "$InstallDir\keys" -Force
    
    # Generate SSL keys
    & openssl genrsa -out "$InstallDir\keys\private.pem" 2048
    & openssl rsa -in "$InstallDir\keys\private.pem" -pubout -out "$InstallDir\keys\public.pem"
    
    # Set permissions
    $acl = Get-Acl "$InstallDir\keys\private.pem"
    $acl.SetAccessRuleProtection($true, $false)
    Set-Acl "$InstallDir\keys\private.pem" $acl
    
    Log-Success "Configuration files created"
}

# Create Windows services
function New-WindowsServices {
    if ($SkipServices) {
        Log-Warning "Skipping Windows services creation"
        return
    }
    
    Log-Info "Creating Windows services..."
    
    $venvPython = "$InstallDir\venv\Scripts\python.exe"
    
    # Backend service
    $backendService = @"
nssm install BreastGuardBackend "$venvPython"
nssm set BreastGuardBackend Arguments "-m uvicorn main:app --host 0.0.0.0 --port 8000"
nssm set BreastGuardBackend DisplayName "BreastGuard AI Backend"
nssm set BreastGuardBackend Description "BreastGuard AI Backend API Service"
nssm set BreastGuardBackend Start SERVICE_AUTO_START
nssm set BreastGuardBackend AppDirectory "$InstallDir\backend"
nssm set BreastGuardBackend Environment "PYTHONPATH=$InstallDir\backend"
"@
    
    # ML Service
    $mlService = @"
nssm install BreastGuardML "$venvPython"
nssm set BreastGuardML Arguments "-m uvicorn main:app --host 0.0.0.0 --port 8001"
nssm set BreastGuardML DisplayName "BreastGuard AI ML Service"
nssm set BreastGuardML Description "BreastGuard AI Machine Learning Service"
nssm set BreastGuardML Start SERVICE_AUTO_START
nssm set BreastGuardML AppDirectory "$InstallDir\ml_service"
nssm set BreastGuardML Environment "PYTHONPATH=$InstallDir\ml_service"
"@
    
    # Document Parser Service
    $parserService = @"
nssm install BreastGuardParser "$venvPython"
nssm set BreastGuardParser Arguments "-m uvicorn main:app --host 0.0.0.0 --port 8002"
nssm set BreastGuardParser DisplayName "BreastGuard AI Document Parser"
nssm set BreastGuardParser Description "BreastGuard AI Document Parser Service"
nssm set BreastGuardParser Start SERVICE_AUTO_START
nssm set BreastGuardParser AppDirectory "$InstallDir\document_parser"
nssm set BreastGuardParser Environment "PYTHONPATH=$InstallDir\document_parser"
"@
    
    # Install NSSM if not present
    if (!(Get-Command nssm -ErrorAction SilentlyContinue)) {
        choco install nssm -y
        refreshenv
    }
    
    # Create services
    $backendService | cmd
    $mlService | cmd
    $parserService | cmd
    
    Log-Success "Windows services created"
}

# Setup Nginx
function Initialize-Nginx {
    Log-Info "Setting up Nginx..."
    
    $nginxConfig = @"
server {
    listen 80;
    server_name localhost;
    
    # Frontend
    location / {
        root $InstallDir\frontend\dist;
        index index.html;
        try_files `$uri `$uri/ /index.html;
    }
    
    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host `$host;
        proxy_set_header X-Real-IP `$remote_addr;
        proxy_set_header X-Forwarded-For `$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto `$scheme;
    }
    
    # ML Service
    location /ml/ {
        proxy_pass http://localhost:8001/;
        proxy_set_header Host `$host;
        proxy_set_header X-Real-IP `$remote_addr;
        proxy_set_header X-Forwarded-For `$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto `$scheme;
    }
    
    # Document Parser
    location /parser/ {
        proxy_pass http://localhost:8002/;
        proxy_set_header Host `$host;
        proxy_set_header X-Real-IP `$remote_addr;
        proxy_set_header X-Forwarded-For `$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto `$scheme;
    }
}
"@
    
    $nginxConfig | Out-File -FilePath "C:\nginx\conf\breastguard.conf" -Encoding UTF8
    
    # Start Nginx service
    Start-Service nginx -ErrorAction SilentlyContinue
    Set-Service nginx -StartupType Automatic
    
    Log-Success "Nginx configured"
}

# Build frontend
function Build-Frontend {
    Log-Info "Building frontend..."
    
    Set-Location $InstallDir\frontend
    npm run build
    
    Log-Success "Frontend built"
}

# Start services
function Start-Services {
    Log-Info "Starting services..."
    
    if (-not $SkipServices) {
        # Start Windows services
        Start-Service BreastGuardBackend -ErrorAction SilentlyContinue
        Start-Service BreastGuardML -ErrorAction SilentlyContinue
        Start-Service BreastGuardParser -ErrorAction SilentlyContinue
        
        # Wait for services to start
        Start-Sleep -Seconds 10
        
        # Check service status
        $services = @("BreastGuardBackend", "BreastGuardML", "BreastGuardParser")
        foreach ($service in $services) {
            $status = Get-Service -Name $service -ErrorAction SilentlyContinue
            if ($status -and $status.Status -eq "Running") {
                Log-Success "$service is running"
            } else {
                Log-Error "$service failed to start"
            }
        }
    } else {
        # Start services manually
        $venvPython = "$InstallDir\venv\Scripts\python.exe"
        
        Start-Process -FilePath $venvPython -ArgumentList "-m uvicorn main:app --host 0.0.0.0 --port 8000" -WorkingDirectory "$InstallDir\backend" -WindowStyle Hidden
        Start-Process -FilePath $venvPython -ArgumentList "-m uvicorn main:app --host 0.0.0.0 --port 8001" -WorkingDirectory "$InstallDir\ml_service" -WindowStyle Hidden
        Start-Process -FilePath $venvPython -ArgumentList "-m uvicorn main:app --host 0.0.0.0 --port 8002" -WorkingDirectory "$InstallDir\document_parser" -WindowStyle Hidden
        
        Log-Success "Services started (manual mode)"
    }
}

# Create admin user
function New-AdminUser {
    Log-Info "Creating admin user..."
    
    $venvPython = "$InstallDir\venv\Scripts\python.exe"
    Set-Location $InstallDir\backend
    
    $createUserScript = @"
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
"@
    
    $createUserScript | & $venvPython
    
    Log-Success "Admin user created"
}

# Main installation function
function Start-Installation {
    Log-Info "Starting BreastGuard AI Windows installation..."
    
    # Check if running as Administrator
    if (-not (Test-Administrator)) {
        Log-Error "This script must be run as Administrator"
        exit 1
    }
    
    Test-SystemRequirements
    Install-Chocolatey
    Install-SystemDependencies
    New-ServiceUser
    Initialize-InstallationDirectory
    Copy-SourceFiles
    Install-PythonDependencies
    Install-NodeDependencies
    Initialize-Databases
    New-ConfigurationFiles
    Invoke-DatabaseMigrations
    Build-Frontend
    New-WindowsServices
    Initialize-Nginx
    Start-Services
    New-AdminUser
    
    Log-Success "BreastGuard AI installation completed!"
    Write-Output ""
    Write-Output "🎉 Installation Complete!"
    Write-Output ""
    Write-Output "Access application at:"
    Write-Output "  Frontend: http://localhost"
    Write-Output "  API: http://localhost/api/v1"
    Write-Output "  Admin: admin@breastguard.ai / admin123"
    Write-Output ""
    Write-Output "Service management:"
    Write-Output "  Start: Start-Service BreastGuardBackend"
    Write-Output "  Stop: Stop-Service BreastGuardBackend"
    Write-Output "  Status: Get-Service BreastGuardBackend"
    Write-Output ""
    Write-Output "Configuration file: $InstallDir\.env"
    Write-Output "Logs: $InstallDir\logs\"
    Write-Output ""
}

# Run main function
Start-Installation
