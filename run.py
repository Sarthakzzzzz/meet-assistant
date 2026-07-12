import asyncio
import logging
import signal
import os
import yaml
from core.event_bus import EventBus
from core.state_manager import StateManager
from web.server import start_web_server
from sensors.browser_sensor import BrowserSensor
from sensors.audio_sensor import AudioSensor
from workers.transcription_worker import TranscriptionWorker
from workers.notification_worker import NotificationWorker
from workers.intelligence_worker import IntelligenceWorker

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/assistant.log", mode="w"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Main")

async def main():
    logger.info("Starting Meet Assistant (WEB UI MODE)...")

    if os.path.exists(".env"):
        try:
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        val_cleaned = val.strip().strip('"').strip("'")
                        os.environ[key.strip()] = val_cleaned
        except Exception as e:
            logger.warning(f"Could not load .env file: {e}")

    try:
        with open("config.yaml", "r") as f:
            config_str = f.read()
            
        import re
        def env_replacer(match):
            var_name = match.group(1) or match.group(2)
            return os.environ.get(var_name, "")
            
        config_str = re.sub(r'\$\{(\w+)\}|\$(\w+)', env_replacer, config_str)
        config = yaml.safe_load(config_str)
    except Exception as e:
        logger.error(f"Failed to load config.yaml: {e}")
        return

    meeting_url = config.get("browser", {}).get("meeting_url", "")
    if "xxx-yyyy-zzz" in meeting_url or not meeting_url:
        logger.error("Set your meeting URL in config.yaml -> browser.meeting_url")
        return

    bus = EventBus()
    state = StateManager()

    browser_sensor = BrowserSensor(bus=bus, config=config)
    audio_sensor = AudioSensor(bus=bus, config=config)

    transcription_worker = TranscriptionWorker(bus=bus, state_manager=state, config=config)
    notification_worker = NotificationWorker(
        topic_url=config.get("notification", {}).get("topic_url")
    )
    intelligence_worker = IntelligenceWorker(bus=bus, state_manager=state, config=config)

    bus.subscribe("AudioChunk", transcription_worker.handle_audio_chunk)
    bus.subscribe("TranscriptUpdated", intelligence_worker.handle_transcript_updated)
    bus.subscribe("ChatReceived", intelligence_worker.handle_chat_received)
    bus.subscribe("TriggerAlert", notification_worker.handle_alert)

    bus.start()

    web_server_task = start_web_server(bus, config)

    try:
        await browser_sensor.start()
        bus.publish("SystemStatus", {"component": "browser", "state": "connected"})
        logger.info("Browser Sensor started.")
    except Exception as e:
        bus.publish("SystemStatus", {"component": "browser", "state": "error"})
        logger.error(f"Browser Sensor failed: {e}")

    try:
        audio_sensor.start()
        bus.publish("SystemStatus", {"component": "audio", "state": "connected"})
        logger.info("Audio Sensor started.")
    except Exception as e:
        bus.publish("SystemStatus", {"component": "audio", "state": "error"})
        logger.warning(f"Audio Sensor failed: {e}")

    shutdown_event = asyncio.Event()

    def handle_shutdown():
        logger.info("Shutdown signal received.")
        shutdown_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_shutdown)

    await shutdown_event.wait()

    logger.info("Shutting down...")
    web_server_task.cancel()
    try:
        await web_server_task
    except asyncio.CancelledError:
        pass
    
    await audio_sensor.stop()
    await browser_sensor.stop()
    await bus.stop()

    logger.info("Meet Assistant shut down cleanly.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user.")
