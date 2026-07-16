# Use the official Playwright Python image (includes OS dependencies for Chromium)
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Install Xvfb for virtual display (needed for headed mode in Docker)
RUN apt-get update && apt-get install -y xvfb && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ensure playwright browsers are correctly linked/installed if needed
RUN playwright install chromium

# Copy application code
COPY . .

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Create directories for persistent volumes
RUN mkdir -p /app/data /app/logs

# Expose FastAPI port
EXPOSE 8000

# Use entrypoint that starts Xvfb then FastAPI
ENTRYPOINT ["/app/entrypoint.sh"]
