import os
import re
import yaml
import asyncio
import logging
from dotenv import load_dotenv
load_dotenv()
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from core.event_bus import EventBus
from core.state_manager import StateManager
from sensors.browser_sensor import BrowserSensor
from workers.notification_worker import NotificationWorker
from workers.intelligence_worker import IntelligenceWorker

# Setup logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/assistant.log", mode="w"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("FastAPIOrc")

# Active frontend WS connections
active_connections = []
global_bus = None

async def broadcast_event(event_type: str, data: dict):
    disconnected = []
    for connection in active_connections:
        try:
            await connection.send_json({"type": event_type, "data": data})
        except Exception:
            disconnected.append(connection)
    
    for conn in disconnected:
        if conn in active_connections:
            active_connections.remove(conn)

from pydantic import BaseModel
from fastapi import HTTPException

# Global references for REST endpoints
global_vector_store = None
global_llm_client = None
global_config = None

class StartMeetingRequest(BaseModel):
    url: str

class ChatQueryRequest(BaseModel):
    text: str

class LoginRequest(BaseModel):
    username: str
    password: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    global global_bus, global_vector_store, global_llm_client, global_config
    logger.info("Starting Meet Assistant Backend (FastAPI Lifespan)...")
    
    # 1. Load configuration
    try:
        config_path = "config.yaml" if os.path.exists("config.yaml") else "config.example.yaml"
        with open(config_path, "r") as f:
            config_str = f.read()
            
        def env_replacer(match):
            var_name = match.group(1) or match.group(2)
            return os.environ.get(var_name, "")
            
        config_str = re.sub(r'\$\{(\w+)\}|\$(\w+)', env_replacer, config_str)
        config = yaml.safe_load(config_str)
        global_config = config
    except Exception as e:
        logger.error(f"Failed to load config.yaml: {e}")
        raise e

    # 2. Setup folders and log files
    if not os.path.exists("logs/meeting_notes.md") or os.path.getsize("logs/meeting_notes.md") == 0:
        with open("logs/meeting_notes.md", "w", encoding="utf-8") as f:
            f.write("# Meeting Notes & Transcripts\n\n")

    session_state = {"current_slide_path": None}

    # 3. Initialize components
    bus = EventBus()
    global_bus = bus
    state = StateManager()

    browser_sensor = BrowserSensor(bus=bus, config=config)
    notification_worker = NotificationWorker(
        topic_url=config.get("notification", {}).get("topic_url")
    )
    intelligence_worker = IntelligenceWorker(bus=bus, state_manager=state, config=config)
    
    # Populate global references for REST APIs
    global_vector_store = intelligence_worker.vector_store
    global_llm_client = intelligence_worker.llm_client

    # 4. Web server routing callbacks (mapping bus events to frontend WebSockets)
    async def on_transcript(payload):
        text = payload.get("text", "") if isinstance(payload, dict) else str(payload)
        speaker = payload.get("speaker", "Speaker") if isinstance(payload, dict) else "Speaker"
        await broadcast_event("transcript", {"speaker": speaker, "text": text})

    async def on_chat(text):
        await broadcast_event("chat", {"text": text, "source": "meeting"})

    async def on_alert(payload):
        title = payload.get("title", "Alert") if isinstance(payload, dict) else str(payload)
        await broadcast_event("alert", {"title": title})

    async def on_send_chat(text):
        await broadcast_event("chat", {"text": text, "source": "ai"})

    async def on_status(payload):
        await broadcast_event("status", payload)

    async def on_slide(filepath):
        session_state["current_slide_path"] = filepath
        await broadcast_event("slide_changed", {"filepath": filepath})
        with open("logs/meeting_notes.md", "a", encoding="utf-8") as f:
            f.write(f"\n## Slide: {os.path.basename(filepath)}\n")
            f.write(f"![Slide Image](../{filepath})\n\n")

    async def on_caption(payload):
        text = payload.get("text", "") if isinstance(payload, dict) else str(payload)
        speaker = payload.get("speaker", "Platform CC") if isinstance(payload, dict) else "Platform CC"
        
        with open("logs/captions.txt", "a", encoding="utf-8") as f:
            f.write(f"[{speaker}] {text}\n")
            
        with open("logs/meeting_notes.md", "a", encoding="utf-8") as f:
            if not session_state["current_slide_path"]:
                f.write(f"### [Pre-presentation] {speaker}: {text}\n")
            else:
                f.write(f"- **{speaker}**: {text}\n")
            
        await broadcast_event("caption", {
            "speaker": speaker, 
            "text": text,
            "slide": session_state["current_slide_path"]
        })

    # Wire up the Event Bus subscriptions (Backend internal)
    bus.subscribe("TranscriptUpdated", intelligence_worker.handle_transcript_updated)
    bus.subscribe("ChatReceived", intelligence_worker.handle_chat_received)
    bus.subscribe("PlatformCaption", intelligence_worker.handle_platform_caption)
    bus.subscribe("SlideCaptured", intelligence_worker.handle_slide_captured)
    bus.subscribe("TriggerAlert", notification_worker.handle_alert)

    # Wire up the Event Bus subscriptions (Frontend WebSockets broadcast)
    bus.subscribe("TranscriptUpdated", on_transcript)
    bus.subscribe("ChatReceived", on_chat)
    bus.subscribe("TriggerAlert", on_alert)
    bus.subscribe("SendChat", on_send_chat)
    bus.subscribe("SystemStatus", on_status)
    bus.subscribe("PlatformCaption", on_caption)
    bus.subscribe("SlideCaptured", on_slide)

    # 5. Start Bus & Sensor listener
    bus.start()
    await browser_sensor.start()
    logger.info("Meet Assistant system initialized and running inside FastAPI lifespan.")

    yield

    # 6. Shutdown cleanly
    logger.info("Shutting down Meet Assistant Backend...")
    await browser_sensor.stop()
    await bus.stop()
    logger.info("Clean shutdown complete.")

app = FastAPI(lifespan=lifespan)

# Allow CORS for Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST API Endpoints
@app.post("/api/login")
async def login(request: LoginRequest):
    """Simple username/password auth validated against config.yaml credentials."""
    creds = (global_config or {}).get("auth", {})
    valid_user = creds.get("username") or os.environ.get("MEET_USERNAME")
    valid_pass = creds.get("password") or os.environ.get("MEET_PASSWORD")
    if request.username == valid_user and request.password == valid_pass:
        return {"status": "success", "message": "Logged in"}
    raise HTTPException(status_code=401, detail="Invalid username or password.")

@app.post("/api/start-meeting")
async def start_meeting(request: StartMeetingRequest):
    if global_bus:
        global_bus.publish("StartMeeting", request.url)
        return {"status": "success", "message": f"Launching meeting: {request.url}"}
    return {"status": "error", "message": "Event bus offline"}

@app.post("/api/start-recording")
async def start_recording():
    if global_bus:
        global_bus.publish("StartRecording", {})
        return {"status": "success", "message": "Recording started"}
    return {"status": "error", "message": "Event bus offline"}

@app.post("/api/chat")
async def chat_query(request: ChatQueryRequest):
    if not global_vector_store or not global_llm_client:
        return {"status": "error", "message": "RAG engine offline"}
    
    try:
        # Retrieve context
        docs = global_vector_store.similarity_search(request.text, k=5)
        context = "\n".join([f"[Slide: {d.metadata.get('slide', 'None')}] {d.page_content}" for d in docs])
        
        # Build prompt
        prompt = f"""You are a helpful AI Meeting Assistant. Answer the user's question based on the meeting context below. 
If you don't know the answer based on the context, just say you don't know.

Meeting Context:
{context}

Question: {request.text}
Answer:"""

        # Async query execution
        answer = await asyncio.to_thread(global_llm_client.query, prompt)
        return {"status": "success", "response": answer}
    except Exception as e:
        logger.error(f"Error handling REST chat: {e}")
        return {"status": "error", "message": str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "chat_query":
                text = data.get("text", "")
                if global_bus:
                    global_bus.publish("UserChatQuery", text)
            elif data.get("type") == "start_meeting":
                url = data.get("url", "")
                if global_bus and url:
                    global_bus.publish("StartMeeting", url)
            elif data.get("type") == "start_recording":
                if global_bus:
                    global_bus.publish("StartRecording", {})
    except WebSocketDisconnect:
        active_connections.remove(websocket)

# Mount static folder
app.mount("/data", StaticFiles(directory="data"), name="data")
