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

def start_web_server(bus, config):
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

    bus.subscribe("TranscriptUpdated", on_transcript)
    bus.subscribe("ChatReceived", on_chat)
    bus.subscribe("TriggerAlert", on_alert)
    bus.subscribe("SendChat", on_send_chat)
    bus.subscribe("SystemStatus", on_status)

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
