import logging
import asyncio
from faster_whisper import WhisperModel, download_model

logger = logging.getLogger("TranscriptionWorker")

class TranscriptionWorker:
    def __init__(self, bus, state_manager, config):
        self.bus = bus
        self.state = state_manager
        self.config = config
        
        trans_cfg = config.get("transcription", {})
        self.model_size = trans_cfg.get("model_size", "base.en")
        self.compute_type = trans_cfg.get("compute_type", "int8")
        self.model = None
        self._loading_model = False

    def _load_model(self):
        if self.model is None:
            logger.info(f"Downloading/checking faster-whisper model '{self.model_size}'...")
            model_path = download_model(self.model_size)
            
            logger.info(f"Loading faster-whisper model from '{model_path}' (device=cpu, compute=int8)...")
            self.model = WhisperModel(model_path, device="cpu", compute_type="int8")
            logger.info("faster-whisper model loaded successfully.")

    async def handle_audio_chunk(self, audio_data):
        if self.model is None:
            if self._loading_model:
                return
            
            self._loading_model = True
            logger.info("Triggering model download/load in the background...")
            await asyncio.to_thread(self._load_model)
            self._loading_model = False
            return
        
        try:
            def transcribe_blocking():
                audio_flat = audio_data.flatten()
                segments, info = self.model.transcribe(
                    audio_flat, 
                    beam_size=5,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500)
                )
                text = "".join(segment.text for segment in segments).strip()
                
                cleaned = text.lower().replace(".", "").replace(",", "").replace("?", "").replace("!", "").strip()
                if not cleaned or cleaned in ["you", "you you", "you you you", "dot"]:
                    return ""
                    
                return text

            text = await asyncio.to_thread(transcribe_blocking)
            
            if text:
                logger.info(f"Whisper output: '{text}'")
                self.state.add_transcript(speaker="Lecturer", text=text)
                self.bus.publish("TranscriptUpdated", {"speaker": "Lecturer", "text": text})
                
        except Exception as e:
            logger.error(f"Error transcribing audio chunk: {e}")
