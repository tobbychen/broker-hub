#!/bin/bash
# Broker Agents Startup Script for Linux/Mac
# Usage: ./start.sh

set -e

echo "========================================"
echo "  Broker Agents Starting..."
echo "========================================"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found!"
    echo "Please copy .env.example to .env and fill in your API keys"
    exit 1
fi

# Check if Python virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
    echo "Installing dependencies..."
    source .venv/bin/activate
    pip install -r requirements.txt
else
    echo "Using existing virtual environment..."
    source .venv/bin/activate
fi

echo ""
echo "Starting services..."
echo "- Backend (FastAPI): http://localhost:8000"
echo "- Frontend (Vue):    http://localhost:5173"
echo "- Monitor:           running in background"
echo ""
echo "Press Ctrl+C to stop all services"
echo "========================================"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Stopping services..."
    kill $BACKEND_PID $FRONTEND_PID $MONITOR_PID 2>/dev/null || true
    echo "All services stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend
echo "Starting Backend..."
source .venv/bin/activate
python -m uvicorn dashboard.backend.main:app --reload --port 8000 &
BACKEND_PID=$!

# Start frontend
echo "Starting Frontend..."
cd dashboard/frontend
npm run dev &
FRONTEND_PID=$!
cd ../..

# Start monitor scheduler
echo "Starting Monitor..."
cd /home/user/broker-agents  # Update this path as needed
python -m agents.monitor.scheduler &
MONITOR_PID=$!

echo ""
echo "All services started!"
echo ""

# Wait for any process to exit
wait
