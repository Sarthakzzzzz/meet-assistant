#!/bin/bash

echo "Starting Meet Assistant (Native Execution)..."

# Ensure we are in the project directory
cd "$(dirname "$0")"

# Create a virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate the virtual environment
source venv/bin/activate

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt

# Install Playwright browser
echo "Ensuring Playwright browser is installed..."
playwright install chromium

# Run the assistant
echo "Launching Meet Assistant..."
python run.py
