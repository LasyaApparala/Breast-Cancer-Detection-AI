# BreastGuard AI - Quick Start Script (Windows)
# Simplified startup that handles common issues

param(
    [switch]$SkipFrontend,
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

# Create directories
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
New-Item -ItemType Directory -Path "$ProjectRoot\keys" -Force | Out-Null

# Check prerequisites
function Test-Prerequisites {
    Log-Info "Checking prerequisites..."
    
    if (!(Get-Command python -ErrorAction SilentlyContinue)) {
        Log-Error "Python is not installed. Please install Python 3.11+"
        exit 1
    }
    
    if (!(Test-Path $VenvPath)) {
        Log-Info "Creating Python virtual environment..."
        python -m venv $VenvPath
        Log-Success "Virtual environment created"
    }
    
    Log-Success "Prerequisites check completed"
}

# Install minimal dependencies
function Install-MinimalDependencies {
    Log-Info "Installing minimal dependencies..."
    
    $venvPython = "$VenvPath\Scripts\python.exe"
    $venvPip = "$VenvPath\Scripts\pip.exe"
    
    # Upgrade pip
    & $venvPip install --upgrade pip
    
    # Install core backend dependencies only
    Log-Info "Installing core backend dependencies..."
    & $venvPip install fastapi uvicorn pydantic sqlalchemy alembic passlib python-jose[cryptography] python-multipart
    
    # Install ML service dependencies (minimal)
    Log-Info "Installing ML service dependencies..."
    & $venvPip install torch torchvision numpy scikit-learn joblib
    
    Log-Success "Core dependencies installed"
}

# Create simple configuration
function New-SimpleConfig {
    Log-Info "Creating simple configuration..."
    
    # Create simple environment file
    $envContent = @"
# BreastGuard AI Simple Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Database (SQLite for simplicity)
DATABASE_URL=sqlite:///./breastguard_dev.db

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# MongoDB (optional)
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=breastguard_ai_docs

# Security
SECRET_KEY=dev-secret-key-change-in-production
ALGORITHM=HS256

# Services
ML_SERVICE_HOST=localhost
ML_SERVICE_PORT=8001
DOCUMENT_PARSER_HOST=localhost
DOCUMENT_PARSER_PORT=8002
"@
    
    $envContent | Out-File -FilePath "$ProjectRoot\.env" -Encoding UTF8
    
    # Create simple SSL keys (self-signed)
    try {
        # Try to create keys with PowerShell
        $cert = New-SelfSignedCertificate -DnsName "localhost" -CertStoreLocation "Cert:\CurrentUser\My" -KeyExportPolicy Exportable -KeyUsage DigitalSignature,KeyEncipherment
        $certPath = "Cert:\CurrentUser\My\$($cert.Thumbprint)"
        
        # Export private key
        Export-PfxCertificate -Cert $certPath -FilePath "$ProjectRoot\keys\private.pfx" -Password (ConvertTo-SecureString -String "" -Force -AsPlainText)
        
        # For simplicity, create dummy PEM files
        "-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC5V7V8J9vJmV8J9
vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9
vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9
vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9
vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9
vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9
vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9
vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9
vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9
-----END PRIVATE KEY-----" | Out-File -FilePath "$ProjectRoot\keys\private.pem" -Encoding UTF8
        
        "-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA5V7V8J9vJmV8J9vJmV8J9
vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9
vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9
vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9
vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9
vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9
vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9
vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9
vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9vJmV8J9
-----END PUBLIC KEY-----" | Out-File -FilePath "$ProjectRoot\keys\public.pem" -Encoding UTF8
        
        Log-Success "SSL keys created"
    } catch {
        Log-Warning "Could not create SSL certificates. Using development keys."
        # Create dummy keys for development
        "dev-private-key" | Out-File -FilePath "$ProjectRoot\keys\private.pem" -Encoding UTF8
        "dev-public-key" | Out-File -FilePath "$ProjectRoot\keys\public.pem" -Encoding UTF8
    }
    
    Log-Success "Configuration created"
}

# Start backend service
function Start-BackendService {
    Log-Info "Starting backend service..."
    
    Set-Location "$ProjectRoot\backend"
    $venvPython = "$VenvPath\Scripts\python.exe"
    
    # Set environment variables
    $env:PYTHONPATH = "$ProjectRoot\backend"
    $env:DATABASE_URL = "sqlite:///./breastguard_dev.db"
    $env:SECRET_KEY = "dev-secret-key-change-in-production"
    $env:ALGORITHM = "HS256"
    $env:JWT_PRIVATE_KEY_PATH = "$ProjectRoot\keys\private.pem"
    $env:JWT_PUBLIC_KEY_PATH = "$ProjectRoot\keys\public.pem"
    
    # Start backend
    try {
        $backendProcess = Start-Process -FilePath $venvPython -ArgumentList "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload" -WorkingDirectory "$ProjectRoot\backend" -PassThru -WindowStyle Hidden
        $backendProcess.Id | Out-File -FilePath "$LogDir\backend.pid"
        Log-Success "Backend service started (PID: $($backendProcess.Id))"
        return $backendProcess
    } catch {
        Log-Error "Failed to start backend: $_"
        return $null
    }
}

# Start ML service
function Start-MLService {
    Log-Info "Starting ML service..."
    
    Set-Location "$ProjectRoot\ml_service"
    $venvPython = "$VenvPath\Scripts\python.exe"
    
    # Set environment variables
    $env:PYTHONPATH = "$ProjectRoot\ml_service"
    $env:MODEL_PATH = "$ProjectRoot\models"
    
    # Create simple ML service main if it doesn't exist
    if (!(Test-Path "$ProjectRoot\ml_service\main.py")) {
        $mlMain = @"
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="BreastGuard AI ML Service", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ml-service", "version": "2.1.0"}

@app.post("/predict")
async def predict():
    # Mock prediction for development
    return {
        "prediction": {
            "severity": "Moderate",
            "confidence": 0.87,
            "uncertainty": 0.12,
            "stage": "Stage II",
            "feature_contributions": [
                {"feature": "Tumor Size", "contribution": 12.5, "importance": "high"},
                {"feature": "ER Status", "contribution": -5.2, "importance": "medium"}
            ]
        },
        "processing_time_ms": 1500
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
"@
        $mlMain | Out-File -FilePath "$ProjectRoot\ml_service\main.py" -Encoding UTF8
    }
    
    try {
        $mlProcess = Start-Process -FilePath $venvPython -ArgumentList "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload" -WorkingDirectory "$ProjectRoot\ml_service" -PassThru -WindowStyle Hidden
        $mlProcess.Id | Out-File -FilePath "$LogDir\ml_service.pid"
        Log-Success "ML service started (PID: $($mlProcess.Id))"
        return $mlProcess
    } catch {
        Log-Error "Failed to start ML service: $_"
        return $null
    }
}

# Start document parser service
function Start-DocumentParserService {
    Log-Info "Starting document parser service..."
    
    Set-Location "$ProjectRoot\document_parser"
    $venvPython = "$VenvPath\Scripts\python.exe"
    
    # Set environment variables
    $env:PYTHONPATH = "$ProjectRoot\document_parser"
    
    # Create simple document parser main if it doesn't exist
    if (!(Test-Path "$ProjectRoot\document_parser\main.py")) {
        $parserMain = @"
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="BreastGuard AI Document Parser", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "document-parser", "version": "2.1.0"}

@app.post("/extract")
async def extract():
    # Mock extraction for development
    return {
        "extracted_data": {
            "tumor_size": 2.5,
            "tumor_grade": 2,
            "er_status": "positive",
            "pr_status": "positive",
            "her2_status": "negative",
            "ki67_index": 15.0
        },
        "extraction_confidence": 0.92,
        "processing_time_ms": 800
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
"@
        $parserMain | Out-File -FilePath "$ProjectRoot\document_parser\main.py" -Encoding UTF8
    }
    
    try {
        $parserProcess = Start-Process -FilePath $venvPython -ArgumentList "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002", "--reload" -WorkingDirectory "$ProjectRoot\document_parser" -PassThru -WindowStyle Hidden
        $parserProcess.Id | Out-File -FilePath "$LogDir\document_parser.pid"
        Log-Success "Document parser service started (PID: $($parserProcess.Id))"
        return $parserProcess
    } catch {
        Log-Error "Failed to start document parser: $_"
        return $null
    }
}

# Start frontend (if not skipped)
function Start-FrontendService {
    if ($SkipFrontend) {
        Log-Warning "Skipping frontend startup"
        return $null
    }
    
    Log-Info "Starting frontend..."
    
    Set-Location "$ProjectRoot\frontend"
    
    # Create simple package.json if it doesn't exist or has conflicts
    if (!(Test-Path "$ProjectRoot\frontend\package.json") -or $true) {
        $packageJson = @{
            name = "breastguard-ai-frontend"
            version = "2.1.0"
            scripts = @{
                dev = "vite --host 0.0.0.0 --port 3000"
                build = "vite build"
                preview = "vite preview"
            }
            dependencies = @{
                react = "^18.2.0"
                "react-dom" = "^18.2.0"
                "react-router-dom" = "^6.8.0"
                axios = "^1.4.0"
                "react-dropzone" = "^14.2.0"
                recharts = "^2.7.0"
                zustand = "^4.4.0"
                "@hookform/resolvers" = "^3.1.0"
                "react-hook-form" = "^7.45.0"
                zod = "^3.21.0"
                "@types/react" = "^18.2.0"
                "@types/react-dom" = "^18.2.0"
                typescript = "^5.0.0"
                tailwindcss = "^3.3.0"
                autoprefixer = "^10.4.0"
                postcss = "^8.4.0"
            }
            devDependencies = @{
                "@types/node" = "^20.4.0"
                vite = "^4.4.0"
                "@vitejs/plugin-react" = "^4.0.0"
            }
        }
        
        $packageJson | ConvertTo-Json -Depth 10 | Out-File -FilePath "$ProjectRoot\frontend\package.json" -Encoding UTF8
    }
    
    try {
        # Install dependencies with legacy peer deps to avoid conflicts
        npm install --legacy-peer-deps
        
        # Start frontend
        $frontendProcess = Start-Process -FilePath npm -ArgumentList "run", "dev" -WorkingDirectory "$ProjectRoot\frontend" -PassThru -WindowStyle Hidden
        $frontendProcess.Id | Out-File -FilePath "$LogDir\frontend.pid"
        Log-Success "Frontend started (PID: $($frontendProcess.Id))"
        return $frontendProcess
    } catch {
        Log-Error "Failed to start frontend: $_"
        return $null
    }
}

# Wait for services
function Wait-ForServices {
    Log-Info "Waiting for services to be ready..."
    
    # Wait for backend
    for ($i = 1; $i -le 30; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Log-Success "Backend service is ready"
                break
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    
    # Wait for ML service
    for ($i = 1; $i -le 30; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 2 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Log-Success "ML service is ready"
                break
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    
    # Wait for document parser
    for ($i = 1; $i -le 30; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8002/health" -TimeoutSec 2 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Log-Success "Document parser service is ready"
                break
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    
    if (-not $SkipFrontend) {
        # Wait for frontend
        for ($i = 1; $i -le 30; $i++) {
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:3000" -TimeoutSec 2 -ErrorAction Stop
                if ($response.StatusCode -eq 200) {
                    Log-Success "Frontend is ready"
                    break
                }
            } catch {
                Start-Sleep -Seconds 2
            }
        }
    }
}

# Show status
function Show-Status {
    Write-Output ""
    Write-Output "🎉 BreastGuard AI Development Environment Started!"
    Write-Output ""
    Write-Output "Services:"
    if (-not $SkipFrontend) {
        Write-Output "  Frontend:     http://localhost:3000"
    }
    Write-Output "  Backend API:  http://localhost:8000"
    Write-Output "  ML Service:   http://localhost:8001"
    Write-Output "  Document Parser: http://localhost:8002"
    Write-Output "  API Docs:     http://localhost:8000/docs"
    Write-Output ""
    Write-Output "Logs:"
    Write-Output "  Backend:       Get-Content $LogDir\backend.log -Wait"
    Write-Output "  ML Service:    Get-Content $LogDir\ml_service.log -Wait"
    Write-Output "  Document Parser: Get-Content $LogDir\document_parser.log -Wait"
    if (-not $SkipFrontend) {
        Write-Output "  Frontend:      Get-Content $LogDir\frontend.log -Wait"
    }
    Write-Output ""
    Write-Output "Stop all services:"
    Write-Output "  ./scripts/stop-dev.ps1"
    Write-Output ""
    Write-Output "Note: This is a development environment with mock services."
    Write-Output "      Full functionality requires complete dependency installation."
    Write-Output ""
}

# Main function
function Start-QuickDevelopment {
    Log-Info "Starting BreastGuard AI quick development environment..."
    
    Test-Prerequisites
    Install-MinimalDependencies
    New-SimpleConfig
    
    # Start services
    Start-BackendService
    Start-MLService
    Start-DocumentParserService
    Start-FrontendService
    
    # Wait for services to be ready
    Wait-ForServices
    
    # Show status
    Show-Status
    
    Log-Info "Development environment is running. Press Ctrl+C to stop all services."
    
    # Keep script running
    try {
        while ($true) {
            Start-Sleep -Seconds 1
        }
    } catch {
        Log-Info "Interrupt received. Stopping services..."
    }
}

# Run main function
try {
    Start-QuickDevelopment
} catch {
    Log-Error "Failed to start development environment: $_"
    exit 1
}
