import datetime
import os
import logging

logger = logging.getLogger("StateManager")

class StateManager:
    def __init__(self, transcript_log_path="logs/live_transcript.txt"):
        self.transcript_log_path = transcript_log_path
        self._transcript = []
        self._context = {}
        
        os.makedirs(os.path.dirname(self.transcript_log_path), exist_ok=True)
        
        try:
            with open(self.transcript_log_path, "w", encoding="utf-8") as f:
                f.write(f"--- Session started at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        except Exception as e:
            logger.error(f"Failed to initialize transcript log file: {e}")

    def add_transcript(self, speaker: str, text: str):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "timestamp": timestamp,
            "speaker": speaker,
            "text": text
        }
        self._transcript.append(entry)
        
        log_line = f"[{timestamp}] {speaker}: {text}\n"
        try:
            with open(self.transcript_log_path, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception as e:
            logger.error(f"Failed to write to transcript log file: {e}")
            
        logger.info(f"Transcript added: {speaker}: {text}")

    def get_full_transcript(self) -> str:
        return "\n".join(f"[{entry['timestamp']}] {entry['speaker']}: {entry['text']}" for entry in self._transcript)

    def get_recent_transcript(self, limit: int = 15) -> list:
        return self._transcript[-limit:]

    def update_context(self, key: str, value: any):
        self._context[key] = value
        logger.info(f"Context updated - {key}: {value}")

    def get_context(self, key: str, default=None) -> any:
        return self._context.get(key, default)
