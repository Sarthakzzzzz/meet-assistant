import asyncio
import logging
import numpy as np
import sounddevice as sd

logger = logging.getLogger("AudioSensor")

class AudioSensor:
    def __init__(self, bus, config):
        self.bus = bus
        self.config = config
        
        audio_cfg = config.get("audio", {})
        self.sample_rate = audio_cfg.get("sample_rate", 16000)
        self.channels = audio_cfg.get("channels", 1)
        self.device_index = audio_cfg.get("device_index")
        self.chunk_duration = audio_cfg.get("chunk_duration_seconds", 3)
        
        self.stream = None
        self._running = False
        self._loop_task = None
        self._audio_buffer = []

    def _find_monitor_device(self):
        """Automatically routes PulseAudio to capture from the host system's speaker loopback."""
        try:
            import subprocess
            import os
            
            default_sink = subprocess.check_output(
                ["pactl", "get-default-sink"], text=True
            ).strip()
            
            monitor_source = f"{default_sink}.monitor"
            logger.info(f"Auto-detected system speaker loopback: {monitor_source}")
            
            os.environ["PULSE_SOURCE"] = monitor_source
            return None
            
        except Exception as e:
            logger.warning(f"Could not auto-detect PulseAudio monitor: {e}")
            return None

    def _audio_callback(self, indata, frames, time, status):
        if status:
            logger.warning(f"Audio stream status warning: {status}")
        self._audio_buffer.append(indata.copy())

    async def _producer_loop(self):
        logger.info("Audio accumulation background loop active.")
        target_frames = self.sample_rate * self.chunk_duration
        accumulated_data = []
        accumulated_frames = 0
        
        while self._running:
            while self._audio_buffer:
                chunk = self._audio_buffer.pop(0)
                accumulated_data.append(chunk)
                accumulated_frames += len(chunk)
                
                if accumulated_frames >= target_frames:
                    all_audio = np.concatenate(accumulated_data, axis=0)
                    chunk_to_publish = all_audio[:target_frames]
                    
                    self.bus.publish("AudioChunk", chunk_to_publish)
                    
                    remaining = all_audio[target_frames:]
                    accumulated_data = [remaining] if len(remaining) > 0 else []
                    accumulated_frames = len(remaining)
                    
            await asyncio.sleep(0.1)

    def start(self):
        if self._running:
            return

        selected_device = self.device_index
        if selected_device is None:
            selected_device = self._find_monitor_device()

        logger.info(f"Opening audio input stream on device {selected_device}...")
        self.stream = sd.InputStream(
            device=selected_device,
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=self._audio_callback,
            dtype='float32'
        )
        self.stream.start()
        self._running = True
        self._loop_task = asyncio.create_task(self._producer_loop())
        logger.info("Audio sensor successfully started.")

    async def stop(self):
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        if self.stream:
            self.stream.stop()
            self.stream.close()
        logger.info("Audio sensor offline.")
