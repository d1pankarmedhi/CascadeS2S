#!/bin/bash

# start_local.sh
# Script to start CascadeS2S services locally without Docker

echo "Starting CascadeS2S locally without Docker..."
echo "NOTE: Please ensure you have Redis running locally on port 6379"
echo "NOTE: Please ensure you have Ollama running locally"
echo "Press Ctrl+C to stop all services."
echo ""

# Export environment variables
export REDIS_HOST="localhost"
export OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
export PYTHONPATH="."

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
uvicorn api.main:app --host 0.0.0.0 --port 8000 &

echo "Starting STT Worker..."
python stt-worker/worker.py &

echo "Starting LLM Worker..."
python llm-worker/worker.py &

echo "Starting TTS Worker..."
python tts-worker/worker.py &

# Wait for all background processes to finish
wait
