#!/bin/bash
# Entrypoint script for Meet Assistant Backend
# Uses host X11 display if available, otherwise falls back to Xvfb

if [ -z "$DISPLAY" ]; then
    # No host display available — start Xvfb as fallback
    echo "No DISPLAY set. Starting Xvfb virtual framebuffer..."
    Xvfb :99 -ac -screen 0 1920x1080x24 &
    sleep 1
    export DISPLAY=:99
    echo "Xvfb started on display :99 (browser will NOT be visible on host)"
else
    echo "Using host display: $DISPLAY (browser window will appear on host)"
fi

# Start the FastAPI server
exec fastapi run main.py --port 8000 --host 0.0.0.0
