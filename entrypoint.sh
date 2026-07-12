#!/bin/bash
set -e

echo "🚀 Starting Ollama server in the background..."
ollama serve &

# Wait for Ollama server to become ready
echo "⏳ Waiting for Ollama server to start..."
MAX_RETRIES=30
RETRY_COUNT=0
until curl -s http://localhost:11434/api/tags > /dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "❌ Ollama server failed to start after ${MAX_RETRIES} seconds."
        exit 1
    fi
    sleep 1
done
echo "✅ Ollama server is ready."

# Pull the model if not already cached
MODEL_NAME="${OLLAMA_MODEL:-tinyllama}"
echo "📦 Pulling model '${MODEL_NAME}' (this may take a few minutes on first run)..."
ollama pull "$MODEL_NAME"
echo "✅ Model '${MODEL_NAME}' is ready."

# Launch the application
echo "🎬 Launching Google Meet Assistant..."
exec python run.py
