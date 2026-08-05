#!/bin/bash

# start_local.sh
# Script to start CascadeS2S services locally without Docker

echo "Starting CascadeS2S locally..."
echo "NOTE: Please ensure you have Ollama running locally"
echo "Press Ctrl+C to stop all services."
echo ""

echo "Syncing workspace dependencies..."
uv sync --all-packages
echo ""

# Export environment variables
export OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
export PYTHONPATH="."
export STT_HOST="localhost:50051"
export LLM_HOST="localhost:50052"
export TTS_HOST="localhost:50053"

# Function to clean up background processes on exit
cleanup() {
    echo ""
    echo "Shutting down all services..."
    kill $(jobs -p) 2>/dev/null
    wait $(jobs -p) 2>/dev/null
    echo "All services stopped."
    exit
}

# Trap Ctrl+C (SIGINT) and call cleanup
trap cleanup SIGINT SIGTERM

echo "Starting API on port 8000..."
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000 &

echo "Starting STT Worker..."
uv run python stt-worker/worker.py &

echo "Starting LLM Worker..."
uv run python llm-worker/worker.py &

echo "Starting TTS Worker..."
uv run python tts-worker/worker.py &

echo "Starting Frontend..."
(cd frontend && npm run dev) &

# Wait for all background processes to finish
wait
