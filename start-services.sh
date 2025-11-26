#!/usr/bin/env bash
# Quick script to start backend and frontend services
# Usage: ./start-services.sh [backend|frontend|both]

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE="${1:-both}"
LOG_DIR="${PROJECT_ROOT}/.logs"
mkdir -p "$LOG_DIR"

# PIDs to track
BACKEND_PID=""
FRONTEND_PID=""

# Cleanup function to kill background processes
cleanup() {
    echo ""
    echo "Shutting down services..."
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "Stopping backend (PID: $BACKEND_PID)..."
        kill "$BACKEND_PID" 2>/dev/null || true
        wait "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo "Stopping frontend (PID: $FRONTEND_PID)..."
        kill "$FRONTEND_PID" 2>/dev/null || true
        wait "$FRONTEND_PID" 2>/dev/null || true
    fi
    echo "All services stopped."
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM EXIT

start_backend() {
    echo "Starting Backend..."
    cd "$PROJECT_ROOT/backend"
    poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload \
        > "$LOG_DIR/backend.log" 2>&1 &
    BACKEND_PID=$!
    echo "✓ Backend started (PID: $BACKEND_PID)"
    echo "  Logs: tail -f $LOG_DIR/backend.log"
    echo "  URL:  http://localhost:8000"
}

start_frontend() {
    echo "Starting Frontend..."
    cd "$PROJECT_ROOT/frontend"
    pnpm dev > "$LOG_DIR/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    echo "✓ Frontend started (PID: $FRONTEND_PID)"
    echo "  Logs: tail -f $LOG_DIR/frontend.log"
    echo "  URL:  http://localhost:5173"
}

# Function to monitor and display logs
monitor_logs() {
    if [ "$SERVICE" = "both" ]; then
        echo ""
        echo "=========================================="
        echo "Services running! Press Ctrl+C to stop all"
        echo "=========================================="
        echo ""
        echo "Backend:  http://localhost:8000 (PID: $BACKEND_PID)"
        echo "Frontend: http://localhost:5173 (PID: $FRONTEND_PID)"
        echo ""
        echo "View logs:"
        echo "  Backend:  tail -f $LOG_DIR/backend.log"
        echo "  Frontend: tail -f $LOG_DIR/frontend.log"
        echo "  Both:     tail -f $LOG_DIR/*.log"
        echo ""
        echo "Waiting for services... (Ctrl+C to stop)"
        
        # Wait for processes, checking if they're still alive
        while true; do
            if [ -n "$BACKEND_PID" ] && ! kill -0 "$BACKEND_PID" 2>/dev/null; then
                echo "Backend process died!"
                break
            fi
            if [ -n "$FRONTEND_PID" ] && ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
                echo "Frontend process died!"
                break
            fi
            sleep 1
        done
    elif [ "$SERVICE" = "backend" ]; then
        echo ""
        echo "=========================================="
        echo "Backend running! Press Ctrl+C to stop"
        echo "=========================================="
        echo ""
        tail -f "$LOG_DIR/backend.log" 2>/dev/null || true
    elif [ "$SERVICE" = "frontend" ]; then
        echo ""
        echo "=========================================="
        echo "Frontend running! Press Ctrl+C to stop"
        echo "=========================================="
        echo ""
        tail -f "$LOG_DIR/frontend.log" 2>/dev/null || true
    fi
}

case "$SERVICE" in
    backend)
        start_backend
        sleep 1
        monitor_logs
        ;;
    frontend)
        start_frontend
        sleep 1
        monitor_logs
        ;;
    both)
        echo "Starting both services..."
        start_backend
        sleep 2  # Give backend a moment to start
        start_frontend
        sleep 1  # Give frontend a moment to start
        monitor_logs
        ;;
    *)
        echo "Usage: $0 [backend|frontend|both]"
        exit 1
        ;;
esac
