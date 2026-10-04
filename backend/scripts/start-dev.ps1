# BreastGuard AI - Windows Development Startup Script
# Runs all services in development mode without Docker

param(
    [switch]$SkipDeps,
    [switch]$SkipDatabases
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

# Configuration
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path
$VenvPath = "$ProjectRoot\venv"
$LogDir = "$ProjectRoot\logs"

# Get all running processes
function Get-RunningProcesses {
    return Get-Process | Where-Object { $_.ProcessName -like "*python*" -or $_.ProcessName -like "*node*" }
}

# Check prerequisites
function Test-Prerequisites {
    Log-Info "Checking prerequisites..."
    
    # Check Python
    if (!(Get-Command python -ErrorAction SilentlyContinue)) {
        Log-Error "Python 3 is not installed"
        exit 1
    }
    
    # Check Node.js
    if (!(Get-Command node -ErrorAction SilentlyContinue)) {
        Log-Error "Node.js is not installed"
        exit 1
    }
    
    # Check PostgreSQL
    if (!(Get-Command psql -ErrorAction SilentlyContinue)) {
        Log-Warning "PostgreSQL is not installed. Using SQLite for development."
        $env:DATABASE_URL = "sqlite:///./breastguard_dev.db"
    }
    
    # Check Redis
    if (!(Get-Command redis-server -ErrorAction SilentlyContinue)) {
        Log-Warning "Redis is not installed. Some features may not work."
    }
    
    # Check MongoDB
    if (!(Get-Command mongod -ErrorAction SilentlyContinue)) {
        Log-Warning "MongoDB is not installed. Document storage will be disabled."
    }
    
    Log-Success "Prerequisites check completed"
}

# Setup virtual environment
function Initialize-VirtualEnvironment {
    Log-Info "Setting up Python virtual environment..."
    
    if (!(Test-Path $VenvPath)) {
        & python -m venv $VenvPath
        Log-Success "Virtual environment created"
    } else {
        Log-Info "Virtual environment already exists"
    }
    
    # Activate virtual environment and install dependencies
    $venvPython = "$VenvPath\Scripts\python.exe"
    $venvPip = "$VenvPath\Scripts\pip.exe"
    
    # Upgrade pip
    & $venvPip install --upgrade pip
    
    # Install dependencies
    Log-Info "Installing Python dependencies..."
    & $venvPip install -r "$ProjectRoot\backend\requirements.txt"
    & $venvPip install -r "$ProjectRoot\ml_service\requirements.txt"
    & $venvPip install -r "$ProjectRoot\document_parser\requirements.txt"
    
    Log-Success "Python dependencies installed"
}

# Setup Node.js dependencies
function Initialize-NodeDependencies {
    Log-Info "Setting up Node.js dependencies..."
    
    Set-Location "$ProjectRoot\frontend"
    
    if (!(Test-Path "node_modules")) {
        npm install
        Log-Success "Node.js dependencies installed"
    } else {
        Log-Info "Node.js dependencies already exist"
    }
    
    Set-Location $ProjectRoot
}

# Setup databases
function Initialize-Databases {
    if ($SkipDatabases) {
        Log-Warning "Skipping database setup"
        return
    }
    
    Log-Info "Setting up databases..."
    
    # Create logs directory
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    
    # Start PostgreSQL if available
    if (Get-Command pg_ctl -ErrorAction SilentlyContinue) {
        Start-Service postgresql-x64-13 -ErrorAction SilentlyContinue
        Log-Info "PostgreSQL started"
    }
    
    # Start Redis if available
    if (Get-Command redis-server -ErrorAction SilentlyContinue) {
        Start-Process redis-server -WindowStyle Hidden
        Log-Info "Redis started"
    }
    
    # Start MongoDB if available
    if (Get-Command mongod -ErrorAction SilentlyContinue) {
        $dataPath = "$ProjectRoot\data\mongodb"
        New-Item -ItemType Directory -Path $dataPath -Force | Out-Null
        Start-Process mongod -ArgumentList "--dbpath", $dataPath, "--logpath", "$LogDir\mongodb.log" -WindowStyle Hidden
        Log-Info "MongoDB started"
    }
    
    # Run database migrations
    Set-Location "$ProjectRoot\backend"
    $env:PYTHONPATH = "$ProjectRoot\backend"
    
    if (Test-Path "alembic.ini") {
        & "$VenvPath\Scripts\python.exe" -m alembic upgrade head
        Log-Success "Database migrations completed"
    }
    
    Set-Location $ProjectRoot
}

# Start backend service
function Start-BackendService {
    Log-Info "Starting backend service..."
    
    Set-Location "$ProjectRoot\backend"
    $env:PYTHONPATH = "$ProjectRoot\backend"
    if (-not $env:DATABASE_URL) { $env:DATABASE_URL = "postgresql://breastguard_user:secure_password@localhost:5432/breastguard_ai" }
    if (-not $env:REDIS_URL) { $env:REDIS_URL = "redis://localhost:6379/0" }
    if (-not $env:MONGODB_URL) { $env:MONGODB_URL = "mongodb://localhost:27017" }
    $env:JWT_PRIVATE_KEY_PATH = "$ProjectRoot\keys\private.pem"
    $env:JWT_PUBLIC_KEY_PATH = "$ProjectRoot\keys\public.pem"
    
    # Create SSL keys if they don't exist
    New-Item -ItemType Directory -Path "$ProjectRoot\keys" -Force | Out-Null
    if (!(Test-Path "$ProjectRoot\keys\private.pem")) {
        & openssl genrsa -out "$ProjectRoot\keys\private.pem" 2048
        & openssl rsa -in "$ProjectRoot\keys\private.pem" -pubout -out "$ProjectRoot\keys\public.pem"
        Log-Info "SSL keys generated"
    }
    
    # Start backend in background
    $backendProcess = Start-Process -FilePath "$VenvPath\Scripts\python.exe" -ArgumentList "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload" -WorkingDirectory "$ProjectRoot\backend" -PassThru -WindowStyle Hidden
    $backendProcess.Id | Out-File -FilePath "$LogDir\backend.pid"
    
    Log-Success "Backend service started (PID: $($backendProcess.Id))"
}

# Start ML service
function Start-MLService {
    Log-Info "Starting ML service..."
    
    Set-Location "$ProjectRoot\ml_service"
    $env:PYTHONPATH = "$ProjectRoot\ml_service"
    $env:MODEL_PATH = "$ProjectRoot\models"
    
    # Start ML service in background
    $mlProcess = Start-Process -FilePath "$VenvPath\Scripts\python.exe" -ArgumentList "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload" -WorkingDirectory "$ProjectRoot\ml_service" -PassThru -WindowStyle Hidden
    $mlProcess.Id | Out-File -FilePath "$LogDir\ml_service.pid"
    
    Log-Success "ML service started (PID: $($mlProcess.Id))"
}

# Start document parser service
function Start-DocumentParserService {
    Log-Info "Starting document parser service..."
    
    Set-Location "$ProjectRoot\document_parser"
    $env:PYTHONPATH = "$ProjectRoot\document_parser"
    if (-not $env:TESSERACT_PATH) { $env:TESSERACT_PATH = "C:\Program Files\Tesseract-OCR\tesseract.exe" }
    
    # Start document parser in background
    $parserProcess = Start-Process -FilePath "$VenvPath\Scripts\python.exe" -ArgumentList "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002", "--reload" -WorkingDirectory "$ProjectRoot\document_parser" -PassThru -WindowStyle Hidden
    $parserProcess.Id | Out-File -FilePath "$LogDir\document_parser.pid"
    
    Log-Success "Document parser service started (PID: $($parserProcess.Id))"
}

# Start frontend
function Start-Frontend {
    Log-Info "Starting frontend..."
    
    Set-Location "$ProjectRoot\frontend"
    
    # Start frontend in background
    $frontendProcess = Start-Process -FilePath npm -ArgumentList "run", "dev" -WorkingDirectory "$ProjectRoot\frontend" -PassThru -WindowStyle Hidden
    $frontendProcess.Id | Out-File -FilePath "$LogDir\frontend.pid"
    
    Log-Success "Frontend started (PID: $($frontendProcess.Id))"
}

# Start Celery worker
function Start-CeleryWorker {
    Log-Info "Starting Celery worker..."
    
    Set-Location "$ProjectRoot\backend"
    $env:PYTHONPATH = "$ProjectRoot\backend"
    
    # Start Celery worker in background
    $celeryProcess = Start-Process -FilePath "$VenvPath\Scripts\celery.exe" -ArgumentList "-A", "backend.celery", "worker", "--loglevel=info" -WorkingDirectory "$ProjectRoot\backend" -PassThru -WindowStyle Hidden
    $celeryProcess.Id | Out-File -FilePath "$LogDir\celery.pid"
    
    Log-Success "Celery worker started (PID: $($celeryProcess.Id))"
}

# Wait for services to be ready
function Wait-ForServices {
    Log-Info "Waiting for services to be ready..."
    
    # Wait for backend
    $backendReady = $false
    for ($i = 1; $i -le 30; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Log-Success "Backend service is ready"
                $backendReady = $true
                break
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    
    if (-not $backendReady) {
        Log-Error "Backend service failed to start"
        return $false
    }
    
    # Wait for ML service
    $mlReady = $false
    for ($i = 1; $i -le 30; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 2 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Log-Success "ML service is ready"
                $mlReady = $true
                break
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    
    if (-not $mlReady) {
        Log-Error "ML service failed to start"
        return $false
    }
    
    # Wait for document parser
    $parserReady = $false
    for ($i = 1; $i -le 30; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8002/health" -TimeoutSec 2 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Log-Success "Document parser service is ready"
                $parserReady = $true
                break
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    
    if (-not $parserReady) {
        Log-Error "Document parser service failed to start"
        return $false
    }
    
    # Wait for frontend
    $frontendReady = $false
    for ($i = 1; $i -le 30; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:3000" -TimeoutSec 2 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Log-Success "Frontend is ready"
                $frontendReady = $true
                break
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    
    if (-not $frontendReady) {
        Log-Error "Frontend failed to start"
        return $false
    }
    
    return $true
}

# Show status
function Show-Status {
    Write-Output ""
    Write-Output "🎉 BreastGuard AI Development Environment Started!"
    Write-Output ""
    Write-Output "Services:"
    Write-Output "  Frontend:     http://localhost:3000"
    Write-Output "  Backend API:  http://localhost:8000"
    Write-Output "  ML Service:   http://localhost:8001"
    Write-Output "  Document Parser: http://localhost:8002"
    Write-Output "  API Docs:     http://localhost:8000/docs"
    Write-Output ""
    Write-Output "Logs:"
    Write-Output "  Backend:       Get-Content $LogDir\backend.log -Wait"
    Write-Output "  ML Service:    Get-Content $LogDir\ml_service.log -Wait"
    Write-Output "  Document Parser: Get-Content $LogDir\document_parser.log -Wait"
    Write-Output "  Frontend:      Get-Content $LogDir\frontend.log -Wait"
    Write-Output "  Celery:        Get-Content $LogDir\celery.log -Wait"
    Write-Output ""
    Write-Output "Stop all services:"
    Write-Output "  ./scripts/stop-dev.ps1"
    Write-Output ""
    Write-Output "Create admin user:"
    Write-Output "  cd backend; python -c `"from backend.security.auth import hash_password; from backend.models.user import User; from backend.db import SessionLocal; db=SessionLocal(); admin=User(email='admin@breastguard.ai', name='Admin', role='admin', password_hash=hash_password('admin123')); db.add(admin); db.commit(); print('Admin user created')`""
    Write-Output ""
}

# Cleanup function
function Stop-Services {
    Log-Info "Shutting down services..."
    
    # Stop processes by PID files
    $services = @("backend", "ml_service", "document_parser", "frontend", "celery")
    
    foreach ($service in $services) {
        $pidFile = "$LogDir\$service.pid"
        if (Test-Path $pidFile) {
            $pid = Get-Content $pidFile
            try {
                $process = Get-Process -Id $pid -ErrorAction Stop
                $process.Kill()
                Log-Success "$service stopped"
            } catch {
                Log-Warning "Could not stop $service (PID: $pid)"
            }
            Remove-Item $pidFile -Force
        }
    }
    
    # Kill any remaining processes
    Get-Process | Where-Object { $_.ProcessName -like "*python*" -and $_.MainWindowTitle -like "*uvicorn*" } | Stop-Process -Force
    Get-Process | Where-Object { $_.ProcessName -like "*node*" -and $_.MainWindowTitle -like "*npm*" } | Stop-Process -Force
    
    Log-Success "All services stopped"
}

# Set up signal handlers
$originalErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "SilentlyContinue"

# Main function
function Start-DevelopmentEnvironment {
    Log-Info "Starting BreastGuard AI development environment..."
    
    Test-Prerequisites
    
    if (-not $SkipDeps) {
        Initialize-VirtualEnvironment
        Initialize-NodeDependencies
    }
    
    if (-not $SkipDatabases) {
        Initialize-Databases
    }
    
    # Start all services
    Start-BackendService
    Start-MLService
    Start-DocumentParserService
    Start-CeleryWorker
    Start-Frontend
    
    # Wait for services to be ready
    if (Wait-ForServices) {
        # Show status
        Show-Status
        
        # Keep script running
        Log-Info "Development environment is running. Press Ctrl+C to stop all services."
        
        try {
            while ($true) {
                Start-Sleep -Seconds 1
            }
        } catch {
            Log-Info "Interrupt received. Stopping services..."
        } finally {
            Stop-Services
        }
    } else {
        Log-Error "Failed to start all services"
        Stop-Services
        exit 1
    }
}

# Run main function
try {
    Start-DevelopmentEnvironment
} finally {
    $ErrorActionPreference = $originalErrorActionPreference
}
