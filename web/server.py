import os
import asyncio
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

logger = logging.getLogger("WebServer")

app = FastAPI()
active_connections = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)

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

app.mount("/data", StaticFiles(directory="data"), name="data")

def start_web_server(bus, config):
    session_state = {
        "current_slide_path": None
    }

    # Ensure meeting notes has header
    os.makedirs("logs", exist_ok=True)
    if not os.path.exists("logs/meeting_notes.md") or os.path.getsize("logs/meeting_notes.md") == 0:
        with open("logs/meeting_notes.md", "w", encoding="utf-8") as f:
            f.write("# Meeting Notes & Transcripts\n\n")

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
        # Broadcast slide changed event
        await broadcast_event("slide_changed", {"filepath": filepath})
        
        # Log to meeting_notes.md
        with open("logs/meeting_notes.md", "a", encoding="utf-8") as f:
            f.write(f"\n## Slide: {os.path.basename(filepath)}\n")
            # Embed image with relative path
            f.write(f"![Slide Image](../{filepath})\n\n")

    async def on_caption(payload):
        text = payload.get("text", "") if isinstance(payload, dict) else str(payload)
        speaker = payload.get("speaker", "Platform CC") if isinstance(payload, dict) else "Platform CC"
        
        # Log to raw captions file
        with open("logs/captions.txt", "a", encoding="utf-8") as f:
            f.write(f"[{speaker}] {text}\n")
            
        # Log to structured meeting notes file
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

    async def on_slide_summary(payload):
        slide = payload.get("slide", "")
        summary = payload.get("summary", "")
        if not slide or not summary:
            return
            
        # Log to structured meeting notes file under correct slide
        def update_notes():
            file_path = "logs/meeting_notes.md"
            if not os.path.exists(file_path):
                return
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            slide_name = os.path.basename(slide)
            header = f"## Slide: {slide_name}"
            header_idx = content.find(header)
            if header_idx == -1:
                return
                
            next_header_idx = content.find("## Slide:", header_idx + len(header))
            summary_text = f"\n**AI Slide Summary:**\n{summary}\n\n"
            
            if next_header_idx == -1:
                content += summary_text
            else:
                content = content[:next_header_idx] + summary_text + content[next_header_idx:]
                
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
                
        await asyncio.to_thread(update_notes)
        await broadcast_event("slide_summary", {"slide": slide, "summary": summary})

    bus.subscribe("TranscriptUpdated", on_transcript)
    bus.subscribe("ChatReceived", on_chat)
    bus.subscribe("TriggerAlert", on_alert)
    bus.subscribe("SendChat", on_send_chat)
    bus.subscribe("SystemStatus", on_status)
    bus.subscribe("PlatformCaption", on_caption)
    bus.subscribe("SlideCaptured", on_slide)
    bus.subscribe("SlideSummaryGenerated", on_slide_summary)

    @app.get("/")
    async def get():
        web_dir = os.path.dirname(__file__)
        html_path = os.path.join(web_dir, "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        model_name = config.get("llm", {}).get("model_name", "llama3")
        html_content = html_content.replace("{{MODEL_NAME}}", model_name)
        return HTMLResponse(content=html_content)

    uvicorn_config = uvicorn.Config(app, host="0.0.0.0", port=8081, log_level="error")
    server = uvicorn.Server(uvicorn_config)
    
    logger.info("Web server started at http://localhost:8081")
    return asyncio.create_task(server.serve())
