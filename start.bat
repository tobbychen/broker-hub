@echo off
REM Broker Agents Startup Script for Windows
REM Usage: double-click this file or run: start.bat

echo ========================================
echo   Broker Agents Starting...
echo ========================================
echo.

REM Check if .env exists
if not exist ".env" (
    echo ERROR: .env file not found!
    echo Please copy .env.example to .env and fill in your API keys
    pause
    exit /b 1
)

REM Check if Python virtual environment exists
if not exist ".venv" (
    echo Creating Python virtual environment...
    python -m venv .venv
    echo Installing dependencies...
    call .venv\Scripts\pip install -r requirements.txt
)

echo.
echo Starting services...
echo - Backend (FastAPI): http://localhost:8000
echo - Frontend (Vue):    http://localhost:5173
echo - Monitor:           running in background
echo.
echo Press Ctrl+C to stop all services
echo ========================================
echo.

REM Start backend in new window
start "Broker Backend" cmd /k ".venv\Scripts\python -m uvicorn dashboard.backend.main:app --reload --port 8000"

REM Start frontend in new window
start "Broker Frontend" cmd /k "cd dashboard\frontend && call npm run dev"

REM Start monitor scheduler in new window
start "Broker Monitor" cmd /k ".venv\Scripts\python -m agents.monitor.scheduler"

echo All services started!
echo.
pause
