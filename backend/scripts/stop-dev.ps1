# BreastGuard AI - Windows Development Stop Script
# Stops all development services

param(
    [switch]$KeepDatabases
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
$LogDir = "$ProjectRoot\logs"

# Stop service by PID file
function Stop-Service {
    param(
        [string]$ServiceName
    )
    
    $pidFile = "$LogDir\$ServiceName.pid"
    
    if (Test-Path $pidFile) {
        $pid = Get-Content $pidFile
        try {
            $process = Get-Process -Id $pid -ErrorAction Stop
            $process.Kill()
            Log-Success "$ServiceName stopped (PID: $pid)"
        } catch {
            Log-Warning "$ServiceName PID file exists but process not running"
        }
        Remove-Item $pidFile -Force
    } else {
        Log-Info "$ServiceName PID file not found"
    }
}

# Stop services by process name
function Stop-ByProcessName {
    param(
        [string]$ProcessPattern,
        [string]$ServiceName
    )
    
    $processes = Get-Process | Where-Object { $_.ProcessName -like "*$ProcessPattern*" }
    
    if ($processes) {
        Log-Info "Stopping $ServiceName processes..."
        $processes | ForEach-Object { 
            try {
                $_.Kill()
            } catch {
                Log-Warning "Could not kill process $($_.Id): $($_.Exception.Message)"
            }
        }
        Log-Success "$ServiceName processes stopped"
    } else {
        Log-Info "No $ServiceName processes found"
    }
}

# Stop database services
function Stop-DatabaseServices {
    if ($KeepDatabases) {
        Log-Info "Keeping database services running (-KeepDatabases flag used)"
        return
    }
    
    Log-Info "Stopping database services..."
    
    # Stop PostgreSQL
    $postgresService = Get-Service -Name "postgresql-x64-13" -ErrorAction SilentlyContinue
    if ($postgresService) {
        Stop-Service -Name "postgresql-x64-13" -Force
        Log-Info "PostgreSQL stopped"
    }
    
    # Stop Redis
    $redisProcess = Get-Process -Name "redis-server" -ErrorAction SilentlyContinue
    if ($redisProcess) {
        Stop-Process -Name "redis-server" -Force
        Log-Info "Redis stopped"
    }
    
    # Stop MongoDB
    $mongoProcess = Get-Process -Name "mongod" -ErrorAction SilentlyContinue
    if ($mongoProcess) {
        Stop-Process -Name "mongod" -Force
        Log-Info "MongoDB stopped"
    }
    
    Log-Success "Database services stopped"
}

# Clean up temporary files
function Remove-TemporaryFiles {
    Log-Info "Cleaning up temporary files..."
    
    # Remove PID files
    Get-ChildItem -Path $LogDir -Filter "*.pid" -ErrorAction SilentlyContinue | Remove-Item -Force
    
    # Remove temporary directories
    $tempDirs = @("$ProjectRoot\tmp", "$ProjectRoot\__pycache__")
    foreach ($dir in $tempDirs) {
        if (Test-Path $dir) {
            Remove-Item -Path $dir -Recurse -Force
        }
    }
    
    # Remove Python cache files
    Get-ChildItem -Path $ProjectRoot -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue | Remove-Item -Force
    Get-ChildItem -Path $ProjectRoot -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
    
    Log-Success "Temporary files cleaned up"
}

# Show final status
function Show-FinalStatus {
    Write-Output ""
    Write-Output "🛑 BreastGuard AI Development Environment Stopped"
    Write-Output ""
    Write-Output "All services have been stopped."
    Write-Output "Logs are preserved in: $LogDir"
    Write-Output ""
    Write-Output "To restart development environment:"
    Write-Output "  ./scripts/start-dev.ps1"
    Write-Output ""
}

# Main function
function Stop-DevelopmentEnvironment {
    Log-Info "Stopping BreastGuard AI development environment..."
    
    # Stop individual services
    Stop-Service -ServiceName "backend"
    Stop-Service -ServiceName "ml_service"
    Stop-Service -ServiceName "document_parser"
    Stop-Service -ServiceName "frontend"
    Stop-Service -ServiceName "celery"
    
    # Stop any remaining processes
    Stop-ByProcessName -ProcessPattern "uvicorn" -ServiceName "Backend/ML/Parser Services"
    Stop-ByProcessName -ProcessPattern "celery" -ServiceName "Celery Workers"
    Stop-ByProcessName -ProcessPattern "node" -ServiceName "Frontend Development"
    
    # Stop database services (optional)
    Stop-DatabaseServices
    
    # Clean up
    Remove-TemporaryFiles
    
    # Show final status
    Show-FinalStatus
}

# Run main function
Stop-DevelopmentEnvironment
