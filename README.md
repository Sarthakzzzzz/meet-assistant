# 🤖 Meet Assistant

A modern, decoupled, and event-driven AI meeting assistant designed to supercharge your online meetings. 

Meet Assistant acts as an automated "bot" that joins your Google Meet or Microsoft Teams calls, visually captures slides, scrapes live captions directly from the DOM (bypassing heavy audio processing), and provides an AI Copilot chat interface to query the meeting context in real-time. It can even alert your phone if your name is mentioned!

---

NOTE : the current version is only used for microsoft teams
for that open chat section and caption section on in the meet and view as full focus on speaker 
---

## 🌟 Key Features

- **🗣️ Live DOM Transcription:** Bypasses CPU-heavy audio models by scraping native platform closed captions directly from the browser DOM in real-time. Extremely fast and perfectly accurate.
- **🖼️ Smart Slide Capture:** Visually monitors the presentation area and uses pixel-diffing bounding boxes to automatically capture and index new slides as they appear.
- **💬 RAG Copilot Chat:** Ask questions about what was just discussed or shown on screen. Powered by LangChain, ChromaDB (using `all-MiniLM-L6-v2` embeddings), and Google Gemma 31B Free.
- **🚨 Panic Keyword Alerts:** Push notifications to your phone (via `ntfy.sh`) if someone asks "can you hear me" or calls your name.
- **✨ Premium UI:** A stunning, fully responsive Next.js dashboard featuring dark mode, glassmorphism, dynamic animations, and real-time sync.

---

## 🏗️ Architecture & Tech Stack

The project is cleanly decoupled into a **Next.js Frontend** and a **FastAPI Backend**, communicating via REST and WebSockets. The backend itself is built on an **Event-Driven Architecture (EDA)**.

### 🌐 Frontend (Next.js 15)
- **Framework:** Next.js 15 (App Router)
- **Styling:** Tailwind CSS v4, custom glassmorphic utility classes
- **Animations:** Framer Motion
- **Icons:** Lucide React
- **Features:** Secure login, real-time context pane (slides + transcript), and an interactive Copilot chat.

### ⚙️ Backend (FastAPI & Playwright)
- **API Server:** FastAPI & Uvicorn (Handles REST & WebSockets)
- **Event Bus:** Custom async Pub/Sub broker (`core/event_bus.py`)
- **Automation:** Playwright (Chromium) for headless/headful meeting navigation and DOM scraping (`sensors/browser_sensor.py`).
- **Intelligence (RAG):** LangChain + ChromaDB (`all-MiniLM-L6-v2` embeddings) for local vector storage, integrated with Google Gemma 31B Free via OpenRouter (`workers/intelligence_worker.py`).
- **Notifications:** `ntfy.sh` REST API integrations (`workers/notification_worker.py`).

---

## 📂 Project Structure

```text
meet-assistant/
├── backend/
│   ├── core/
│   │   ├── event_bus.py        # Asynchronous event broker
│   │   ├── state_manager.py    # In-memory session state
│   │   ├── vector_store.py     # ChromaDB RAG Vector Store
│   │   └── llm_client.py       # LLM Client wrapper (LangChain / Google Gemma 31B)
│   ├── sensors/
│   │   └── browser_sensor.py   # Playwright automation & slide/caption scraper
│   ├── workers/
│   │   ├── intelligence_worker.py # RAG pipeline and panic triggers
│   │   └── notification_worker.py # Push alerts via ntfy.sh
│   ├── main.py                 # FastAPI application entrypoint & API routes
│   ├── config.example.yaml     # Template configuration file (Versioned)
│   ├── config.yaml             # Local configuration file (Gitignored)
│   ├── Dockerfile              # Docker configuration for backend
│   └── requirements.txt        # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── app/                # Next.js pages (dashboard, login, meeting)
│   │   ├── components/         # Premium UI components (LiveContextPane, CopilotChat)
│   │   └── hooks/              # WebSocket state management (useMeetingWebSocket)
│   ├── Dockerfile              # Docker configuration for frontend
│   ├── eslint.config.mjs       # ESLint configurations
│   └── package.json            # Node.js dependencies
├── docker-compose.yaml         # Docker Compose orchestration config
├── start.sh                    # Native startup script
└── README.md                   # This file
```

---

## 🔒 Configuration & Security

### 1. Environment Variables
To keep your API keys and endpoints secure, you must create `.env` files from the provided templates. **These files are ignored by Git.**

**Root/Backend `.env`** (Copy `.env.example` to `.env` in the root or `backend/` folder):
```env
# OpenRouter API Key for online LLMs
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Push Notification Alert Topic (via ntfy.sh)
NTFY_TOPIC_URL=https://ntfy.sh/your-unique-topic

# Dashboard UI login credentials (Highly recommended to change from defaults)
MEET_USERNAME=your_username_here
MEET_PASSWORD=your_secure_password_here
```

**Frontend `.env.local`** (Copy `frontend/.env.local.example` to `frontend/.env.local`):
```env
# Ensure the frontend points to the correct FastAPI backend port
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_PLAYWRIGHT_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

### 2. Application Config (`backend/config.yaml`)
Copy the provided `backend/config.example.yaml` file to `backend/config.yaml`.
Customize behavior, auth credentials, and platform specific DOM selectors in `backend/config.yaml`.

```yaml
app:
  platform: "microsoft_teams" # Options: "google_meet", "microsoft_teams"

auth:
  username: "admin"
  password: "meetassistant"

llm:
  provider: "openrouter" # Uses Google Gemma 31B Free via OpenRouter by default
  panic_keywords:
    - "can you hear me"
    - "are you there"
```
*Note: Because Google Meet and Microsoft Teams frequently update their UIs, the CSS selectors for chat input, presentation areas, and captions are fully abstracted into `config.yaml` for easy updates without changing the python code.*

---

## 🚀 Installation & Running

### Option A: Using Docker (Recommended)

1. Ensure Docker and Docker Compose are installed on your machine.
2. Verify you have created the required environment files:
   - `backend/.env`
   - `frontend/.env.local`
3. Start the application by running the following command in the root directory:
```bash
docker compose up --build
```
* The backend API will be available at **http://localhost:8000**
* The frontend UI will be available at **http://localhost:3000**

### Option B: Running Natively

**1. Start the Backend Server**
Open a terminal and navigate to the backend directory:
```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install python dependencies
pip install -r requirements.txt

# Install Playwright browser binaries
python -m playwright install --with-deps chromium

# Run the FastAPI server
fastapi dev main.py
```

**2. Start the Frontend Application**
Open a new terminal and navigate to the frontend directory:
```bash
cd frontend

# Install node modules
npm install

# Start the Next.js development server
npm run dev
```

---

## 💡 How to Use

1. Navigate to **http://localhost:3000** in your browser.
2. Enter your meeting URL (Teams or Google Meet) on the landing page and click **Join Meeting**.
3. Log in using the credentials defined in your `config.yaml` (default: `admin` / `meetassistant`).
4. In the background, Playwright will open a chromium window and navigate to the meeting. **You must manually allow permissions and click "Join" in that automated browser window.**
5. **CRITICAL:** You **must turn on Closed Captions (CC)** inside the automated Google Meet or Teams window. The bot relies on these DOM elements to read the transcript.
6. Click **Start Recording** in the Next.js UI to activate the sensors.
7. Use the Copilot Chat on the right to ask questions, while watching the live transcript and active slides update automatically on the left!
