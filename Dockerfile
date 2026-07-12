# Use the official Playwright Python image
FROM mcr.microsoft.com/playwright/python:v1.61.0-jammy
# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Install system dependencies
# Install system dependencies (portaudio, pulseaudio, dbus)
RUN apt-get update && apt-get install -y \
    libportaudio2 \
    portaudio19-dev \
    libasound2-plugins \
    pulseaudio \
    pulseaudio-utils \
    dbus-x11 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Configure ALSA to use PulseAudio directly
RUN echo "pcm.!default { type pulse }" > /etc/asound.conf && \
    echo "ctl.!default { type pulse }" >> /etc/asound.conf

WORKDIR /app
# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Copy the rest of the application
COPY . .
# Default command
CMD ["python", "run.py"]