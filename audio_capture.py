import pyaudiowpatch as pyaudio
import numpy as np
import threading
import queue
import logging

from scipy import signal

logger = logging.getLogger("LiveSub")

class AudioCapture(threading.Thread):
    def __init__(self, device_index=None, sample_rate=16000, chunk_size=8192):
        super().__init__(daemon=True)
        self.p = pyaudio.PyAudio()
        self.device_index = device_index
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size # Increased for high sample rates
        self.audio_queue = queue.Queue()
        self.running = False
        
        if self.device_index is None or self.device_index == -1:
            self.device_index = self._find_loopback_device()
            
    def _find_loopback_device(self):
        # Find the default loopback device
        logger.info("Looking for loopback devices...")
        wasapi_info = self.p.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_speakers = self.p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
        
        logger.info(f"Default speakers: {default_speakers['name']}")
        
        for loopback in self.p.get_loopback_device_info_generator():
            logger.info(f"Checking loopback: {loopback['name']}")
            if default_speakers["name"] in loopback["name"]:
                logger.info(f"Selected loopback device: {loopback['name']} (ID: {loopback['index']})")
                return loopback["index"]
        
        # Fallback: list all and pick the first with [Loopback]
        for i in range(self.p.get_device_count()):
            dev = self.p.get_device_info_by_index(i)
            if dev.get("isLoopbackDevice") and dev["hostApi"] == wasapi_info["index"]:
                logger.info(f"Fallback selected loopback: {dev['name']} (ID: {i})")
                return i
                
        return wasapi_info["defaultOutputDevice"]

    def run(self):
        self.running = True
        device_info = self.p.get_device_info_by_index(self.device_index)
        
        # Adjust sample rate if the device requires it
        actual_sample_rate = int(device_info["defaultSampleRate"])
        
        stream = self.p.open(
            format=pyaudio.paFloat32,
            channels=device_info["maxInputChannels"],
            rate=actual_sample_rate,
            input=True,
            input_device_index=self.device_index,
            frames_per_buffer=self.chunk_size
        )
        
        print(f"Started recording from: {device_info['name']} at {actual_sample_rate}Hz")
        
        try:
            while self.running:
                data = stream.read(self.chunk_size, exception_on_overflow=False)
                audio_chunk = np.frombuffer(data, dtype=np.float32)
                
                # Convert to mono if necessary
                if device_info["maxInputChannels"] > 1:
                    audio_chunk = audio_chunk.reshape(-1, device_info["maxInputChannels"]).mean(axis=1).astype(np.float32)
                
                # Resample to 16kHz if needed (Whisper expects 16kHz)
                if actual_sample_rate != 16000:
                    num_samples = int(len(audio_chunk) * 16000 / actual_sample_rate)
                    audio_chunk = signal.resample(audio_chunk, num_samples).astype(np.float32)
                
                # Final safety cast
                audio_chunk = audio_chunk.astype(np.float32)
                self.audio_queue.put(audio_chunk)
        finally:
            stream.stop_stream()
            stream.close()
            self.p.terminate()

    def stop(self):
        self.running = False
