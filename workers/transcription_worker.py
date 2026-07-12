import logging
import asyncio
import numpy as np
from scipy.io import wavfile

logger = logging.getLogger("TranscriptionWorker")

class TranscriptionWorker:
    def __init__(self, bus, state_manager, config):
        self.bus = bus
        self.state = state_manager
        self.config = config
        
        trans_cfg = config.get("transcription", {})
        self.model_name = trans_cfg.get("model_name", "nvidia/canary-1b-v2")
        self.model = None
        self._loading_model = False

    def _load_model(self):
        if self.model is None:
            logger.info(f"Downloading/loading NVIDIA NeMo model '{self.model_name}' (this may take a while)...")
            # The progress bar is printed to stdout natively by NeMo/HuggingFace during download.
            import nemo.collections.asr as nemo_asr
            self.model = nemo_asr.models.ASRModel.from_pretrained(self.model_name)
            
            logger.info("Moving model to GPU (cuda)...")
            try:
                self.model.to("cuda")
                logger.info("NVIDIA Canary model successfully loaded onto GPU.")
            except Exception as e:
                logger.warning(f"Failed to move model to GPU (is CUDA available?). Running on CPU... {e}")
                self.model.to("cpu")

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
                # audio_data is a numpy float32 array
                audio_flat = audio_data.flatten()
                
                # Write to temp wav file for NeMo to process
                temp_path = "/tmp/chunk.wav"
                wavfile.write(temp_path, 16000, audio_flat)
                
                # Transcribe
                transcriptions = self.model.transcribe([temp_path])
                
                if isinstance(transcriptions, tuple):
                    # Some NeMo models return a tuple (texts, logits)
                    transcriptions = transcriptions[0]
                    
                if transcriptions and len(transcriptions) > 0:
                    text = transcriptions[0].strip()
                    
                    cleaned = text.lower().replace(".", "").replace(",", "").replace("?", "").replace("!", "").strip()
                    if not cleaned or cleaned in ["you", "you you", "you you you", "dot"]:
                        return ""
                        
                    return text
                return ""

            text = await asyncio.to_thread(transcribe_blocking)
            
            if text:
                logger.info(f"Canary output: '{text}'")
                self.state.add_transcript(speaker="Lecturer", text=text)
                self.bus.publish("TranscriptUpdated", {"speaker": "Lecturer", "text": text})
                
        except Exception as e:
            logger.error(f"Error transcribing audio chunk: {e}")
