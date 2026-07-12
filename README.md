# Meet Assistant

An event-driven AI meeting assistant running in Docker. It captures system audio to transcribe meetings in real-time, monitors the chat using Playwright, and leverages cloud LLMs (via OpenRouter) to automatically draft responses when you are mentioned.

---

## 🛠️ Tech Stack

* **Core Runtime:** Python 3.10
* **Event Broker:** Asynchronous Event Bus (built on `asyncio.Queue`)
* **Browser Automation & DOM Monitoring:** Playwright (Python async API)
* **Speech-to-Text (ASR):** `nvidia/canary-1b-v2` (Running on GPU via NVIDIA NeMo toolkit)
* **Audio Capture:** `sounddevice`, `numpy`, and PortAudio (mapped to host PulseAudio/PipeWire)
* **Large Language Model (LLM):** OpenRouter API (default: `google/gemma-4-31b:free`)
* **Web Server & WebSocket Stream:** FastAPI & Uvicorn 
* **Push Notifications:** `ntfy.sh` (REST endpoint for instant mobile alerts)
* **Containerization:** Docker (official Playwright-based Linux container + PyTorch CUDA 12.1)

---

## Architecture & File Structure

This project is built around an **Event-Driven Architecture (EDA)**. Independent **Sensors** collect environmental data and publish events to a central **Event Bus**, which asynchronously routes them to **Workers** to perform tasks (like transcribing and thinking).

### File Structure
```text
meet-assistant/
├── core/
│   ├── event_bus.py        # Asynchronous event broker
│   └── state_manager.py    # In-memory transcript buffers
├── sensors/
│   ├── audio_sensor.py     # Audio capture using PortAudio loopback
│   └── browser_sensor.py   # Playwright browser automation
├── workers/
│   ├── transcription_worker.py  # NVIDIA Canary-1B GPU speech-to-text
│   ├── intelligence_worker.py   # Panic keyword analyzer & OpenRouter API client
│   └── notification_worker.py   # Real-time mobile push alerts via ntfy.sh
├── web/
│   ├── index.html          # Web UI live dashboard template
│   └── server.py           # FastAPI/WebSocket server
├── config.yaml             # General app options and selector definitions
├── requirements.txt        # Python package dependencies
├── Dockerfile              # Container definition
├── .env                    # (Git-ignored) Secure API keys and URLs
└── run.py                  # App entrypoint
```

---

## Security Configuration (.env)

Sensitive keys and private meeting links must be stored in a `.env` file in the root directory. **Never commit this file to git.**

Create a `.env` file in the root folder:
```env
# OpenRouter API Key for online LLM
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Meeting URL (Teams or Google Meet)
MEETING_URL=https://teams.live.com/...

# Push Notification Alert Topic (via ntfy.sh)
NTFY_TOPIC_URL=https://ntfy.sh/your-unique-topic

# (Optional) Hugging Face Token for authenticated model downloads
HF_TOKEN=hf_your-token-here
```

The application's `run.py` dynamically resolves environment variable placeholders in `config.yaml` (e.g. `${OPENROUTER_API_KEY}`) on-the-fly.

### Platform Configuration (`config.yaml`)

Because Google Meet and Microsoft Teams have completely different web interfaces, you **must** specify your platform in `config.yaml` so the browser bot knows which CSS selectors to use.

```yaml
# config.yaml
app:
  platform: "microsoft_teams" # Options: "google_meet", "microsoft_teams"
```
You can also tweak transcription speeds, keyword triggers, and audio device mappings in this file.

---

## Running with Docker

### 1. Build the Image
```bash
sudo docker build -t meet-assistant .
```

### 2. Run the Container
Run the container with X11 display mapping, local audio mapping, environment variables, and local HuggingFace cache directory.

*(Note: We use `--net=host` to smoothly connect to PulseAudio and the X11 server. We use `--gpus all` to pass your NVIDIA GPU through to the container so that PyTorch can run Canary rapidly).*

```bash
sudo docker run --rm -it \
    --gpus all \
    --net=host \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v /run/user/1000/pulse/native:/run/user/1000/pulse/native \
    -e PULSE_SERVER=unix:/run/user/1000/pulse/native \
    -v huggingface_cache:/root/.cache/huggingface \
    -v $(pwd):/app \
    --env-file .env \
    meet-assistant
```

### 3. Open the Dashboard
Once started, go to **[http://localhost:8081](http://localhost:8081)** to watch live transcripts and AI responses.

---

## Important Information

* **HuggingFace Cache:** The `-v huggingface_cache:...` mount is critical. It caches the 1B parameter Canary model on your host computer so it only downloads once.
* **Audio Routing:** The application auto-detects your system's default speaker and routes it as a loopback source. You can mute your physical speakers, and the bot will still transcribe perfectly.
* **GPU vs CPU:** The transcription worker is configured to run on your GPU via PyTorch CUDA. Ensure you have installed the NVIDIA Container Toolkit on your host machine to allow Docker to access the GPU.
