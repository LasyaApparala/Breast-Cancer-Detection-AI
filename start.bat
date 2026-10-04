@echo off
REM BreastGuard AI - Windows Startup Script
REM Supports both Docker and Local Development

setlocal enabledelayedexpansion

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║    BreastGuard AI - Clinical Decision Support System      ║
echo ║              Starting Application...                       ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM Check if .env exists
if not exist ".env" (
    echo ✅ Creating .env from .env.example...
    copy .env.example .env
    echo    .env created. You can edit it if needed.
) else (
    echo ✅ .env already exists
)

echo.
echo Choose startup method:
echo.
echo   1) Docker Compose (Recommended - All services containerized)
echo   2) Local Development (Backend + Frontend locally)
echo   3) Local Full (All services locally)
echo.

set /p OPTION="Select option (1-3): "

if "%OPTION%"=="1" (
    echo.
    echo 🐳 Starting with Docker Compose...
    echo.
    
    REM Check if Docker is running
    docker info >nul 2>&1
    if errorlevel 1 (
        echo ❌ ERROR: Docker is not running!
        echo    Start Docker Desktop and try again.
        exit /b 1
    )
    
    REM Build and start
    echo 📦 Building images (this may take 2-5 minutes on first run)...
    call docker-compose up --build -d
    
    echo.
    echo ⏳ Waiting for services to be healthy...
    timeout /t 10 /nobreak
    
    echo.
    echo 📊 Service Status:
    call docker-compose ps
    
    echo.
    echo ✅ Services started!
    echo.
    echo 🌐 Access the application:
    echo    Frontend:  http://localhost:3000
    echo    API Docs:  http://localhost:8000/docs
    echo    Health:    http://localhost:8000/health
    echo.
    echo 📋 Useful commands:
    echo    View logs:   docker-compose logs -f backend
    echo    Stop:        docker-compose down
    echo    Full reset:  docker-compose down -v

) else if "%OPTION%"=="2" (
    echo.
    echo 🖥️  Starting Local Development (Backend + Frontend only)...
    echo.
    echo This setup:
    echo   ✅ Backend API (FastAPI) on port 8000
    echo   ✅ Frontend (React) on port 3000
    echo   ✅ SQLite database (local)
    echo.
    
    REM Check Python
    python --version >nul 2>&1
    if errorlevel 1 (
        echo ❌ ERROR: Python 3 not found!
        echo    Install Python 3.11+ and try again.
        exit /b 1
    )
    
    REM Check Node.js
    npm --version >nul 2>&1
    if errorlevel 1 (
        echo ❌ ERROR: Node.js/npm not found!
        echo    Install Node.js 18+ and try again.
        exit /b 1
    )
    
    echo.
    echo Starting Backend and Frontend...
    echo.
    
    REM Start Backend
    echo 🔧 Starting Backend (in new window)...
    start "BreastGuard Backend" cmd /k "cd backend\api && if not exist venv python -m venv venv && call venv\Scripts\activate && pip install -q -r requirements.txt && echo ✅ Backend running at http://localhost:8000 && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
    
    timeout /t 3 /nobreak
    
    REM Start Frontend
    echo 🎨 Starting Frontend (in new window)...
    start "BreastGuard Frontend" cmd /k "cd ui\frontend && npm install -q 2>nul || echo. && echo ✅ Frontend running at http://localhost:3000 && npm run dev -- --host 0.0.0.0"
    
    echo.
    echo ✅ Both services started in new windows!
    echo.
    echo 🌐 Access the application:
    echo    Frontend:  http://localhost:3000
    echo    API Docs:  http://localhost:8000/docs
    echo.
    echo 📋 Close the terminal windows to stop services

) else if "%OPTION%"=="3" (
    echo.
    echo 🔧 Starting Full Local Stack...
    echo.
    echo Please start these services in separate terminals:
    echo.
    echo Terminal 1 (Backend):
    echo   cd backend\api
    echo   if not exist venv python -m venv venv
    echo   call venv\Scripts\activate
    echo   pip install -r requirements.txt
    echo   uvicorn main:app --port 8000 --reload
    echo.
    echo Terminal 2 (Frontend):
    echo   cd ui\frontend
    echo   npm install
    echo   npm run dev
    echo.
    echo Terminal 3 (ML Service):
    echo   cd ai\ml_service
    echo   if not exist venv python -m venv venv
    echo   call venv\Scripts\activate
    echo   pip install -r requirements.txt
    echo   uvicorn main:app --port 8001 --reload
    echo.
    echo Then access:
    echo   Frontend:  http://localhost:3000
    echo   API Docs:  http://localhost:8000/docs

) else (
    echo ❌ Invalid option. Please select 1, 2, or 3.
    exit /b 1
)

endlocal
