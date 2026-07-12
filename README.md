# Meet Assistant

A local, privacy-first AI meeting assistant that runs fully in Docker. It leverages an event-driven architecture to automate joining meetings, capturing audio, and using LLMs (local or cloud) to automatically reply to panic keywords.

---

## Architecture & File Structure

This project is built around an **Event-Driven Architecture (EDA)**. Independent **Sensors** collect environmental data and publish events to a central **Event Bus**, which asynchronously routes them to **Workers** to perform tasks (like transcribing and thinking).

### File Structure
```text
meet-assistant/
├── core/
│   ├── event_bus.py        # Asynchronous event broker using asyncio.Queue
│   └── state_manager.py     # In-memory transcript buffers and slide context
├── sensors/
│   ├── audio_sensor.py      # Audio capture using PortAudio loopback monitor
│   └── browser_sensor.py    # Playwright browser automation (joins, chats, slides)
├── workers/
│   ├── transcription_worker.py  # Local faster-whisper CPU speech-to-text
│   ├── intelligence_worker.py   # Panic keyword analyzer & LLM responder
│   └── notification_worker.py   # Real-time mobile push alerts via ntfy.sh
├── web/
│   ├── index.html           # Web UI live dashboard template
│   └── server.py            # FastAPI/WebSocket server bridging Event Bus to browser
├── config.yaml              # General app options and selector definitions
├── requirements.txt         # Python package dependencies
├── Dockerfile               # Container definition (Playwright-based)
└── run.py                   # App entrypoint
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

# (Optional) Hugging Face Token for authenticated downloads
HF_TOKEN=hf_your-token-here
```

The application's `run.py` dynamically resolves environment variable placeholders in `config.yaml` (e.g. `${OPENROUTER_API_KEY}`) on-the-fly.

---

## Running with Docker

### 1. Build the Image
```bash
sudo docker build -t meet-assistant .
```

### 2. Run the Container
Run the container with X11 display mapping, local audio mapping, environment variables, and local HuggingFace cache directory (prevents downloading models on every run):

```bash
sudo docker run --rm -it \
    --gpus all \
    --net=host \
    -p 8081:8081 \
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

* **HuggingFace Cache:** The `-v huggingface_cache:...` mount is critical. It caches the 1.5 GB `medium` Whisper model on your host computer so it only downloads once. Subsequent runs start instantly.
* **Audio Routing:** The application auto-detects your system's default speaker and routes it as a loopback source. You can mute your physical speakers, and the bot will still transcribe perfectly.
* **CPU vs GPU:** The transcription worker is configured to run on CPU with `int8` quantization. This avoids requiring heavy CUDA configurations inside the container, saving disk space while keeping latency under 2 seconds.
