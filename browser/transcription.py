from faster_whisper import WhisperModel
import threading
import numpy as np
import os
import sys
import queue
import time
import logging

logger = logging.getLogger("LiveSub")

# Fix for CUDA DLLs on Windows
def setup_cuda_dlls():
    if sys.platform == "win32":
        # Paths to search
        search_paths = [
            os.path.join(sys.prefix, "Lib", "site-packages"),
            os.path.join(os.path.dirname(sys.executable), "Lib", "site-packages"),
        ]
        import site
        search_paths.extend(site.getsitepackages())
        
        added = False
        for packages_dir in set(search_paths):
            if not os.path.exists(packages_dir):
                continue
                
            nvidia_dir = os.path.join(packages_dir, "nvidia")
            if os.path.exists(nvidia_dir):
                for sub in os.listdir(nvidia_dir):
                    bin_dir = os.path.join(nvidia_dir, sub, "bin")
                    if os.path.exists(bin_dir):
                        print(f"Adding DLL directory: {bin_dir}")
                        try:
                            os.add_dll_directory(bin_dir)
                            # Also add to PATH for legacy support
                            os.environ["PATH"] = bin_dir + os.pathsep + os.environ["PATH"]
                            added = True
                        except Exception as e:
                            print(f"Failed to add {bin_dir}: {e}")
        
        if not added:
            print("Warning: Could not find NVIDIA CUDA DLLs in site-packages.")

setup_cuda_dlls()

class TranscriptionWorker(threading.Thread):
    def __init__(self, audio_queue, result_callback, status_callback, settings=None):
        super().__init__(daemon=True)
        self.audio_queue = audio_queue
        self.result_callback = result_callback
        self.status_callback = status_callback
        self.settings = settings or {}
        self.running = False
        self.model_v3 = None # GPU Primary
        self.model_v2 = None # GPU Secondary
        self.model_cpu = None # RAM/CPU Verify
        
        self.sample_rate = 16000
        self.buffer = [] 
        self.max_buffer_len = self.sample_rate * 3600 # 1 ora di storia in RAM
        self.process_interval = 0.2 
        self.last_display_text = ""

    def run(self):
        # 1. Load Model with UI feedback
        import ctranslate2
        
        # Get settings with defaults
        pref_device = self.settings.get("device", "auto")
        if pref_device == "auto":
            device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
        else:
            device = pref_device
            
        pref_compute = self.settings.get("compute_type", "auto")
        if pref_compute == "auto":
            compute_type = "float16" if device == "cuda" else "int8"
        else:
            compute_type = pref_compute
            
        model_size = self.settings.get("model_size", "large-v3-turbo")
        use_stacking = self.settings.get("use_stacking", False)
        
        self.status_callback(f"Inizializzazione IA ({model_size})...")
        
        try:
            logger.info(f"Loading primary model: {model_size} on {device}")
            self.model_v3 = WhisperModel(
                model_size, 
                device=device, 
                compute_type=compute_type,
                num_workers=2
            )
            
            if use_stacking:
                logger.info("Loading secondary stacking models...")
                # 2. LARGE-V2 CPU (Spostato qui per liberare la GPU)
                self.status_callback("Caricamento Large-V2 (CPU, RAM)...")
                self.model_v2 = WhisperModel(
                    "large-v2", 
                    device="cpu", 
                    compute_type="int8",
                    cpu_threads=4
                )
                
                # 3. LARGE-V3 CPU (Saturazione RAM)
                self.status_callback("Caricamento Large-V3 (CPU, RAM Titan)...")
                self.model_cpu = WhisperModel(
                    "large-v3", 
                    device="cpu", 
                    compute_type="int8", # Cambiato a int8 per compatibilità universale
                    cpu_threads=4
                )
                self.status_callback(f"Mega-Stacking Attivo ({model_size}).")
            else:
                # Single Model Mode
                self.status_callback(f"Caricamento {model_size} ({device}, {compute_type})...")
                self.model_v2 = None
                self.model_cpu = None
                self.status_callback(f"IA Pronta ({model_size}).")
            
            time.sleep(0.5)
        except Exception as e:
            self.status_callback(f"Errore caricamento: {e}. Ripiego su Tiny...")
            self.model_v3 = WhisperModel("tiny", device="cpu", compute_type="int8")
            self.status_callback("Pronto (Modalità Provvisoria).")
        
        self.running = True
        while self.running:
            try:
                # 1. Raccolta Audio
                while not self.audio_queue.empty():
                    self.buffer.extend(self.audio_queue.get())
                
                if len(self.buffer) > self.max_buffer_len:
                    self.buffer = self.buffer[-self.max_buffer_len:]
                
                if len(self.buffer) >= self.sample_rate * 0.2:
                    # 2. Pre-elaborazione Leggera (AGC & Context Window)
                    context_seconds = float(self.settings.get("context_window", 5.0))
                    raw_audio = np.array(self.buffer, dtype=np.float32)[-int(self.sample_rate * context_seconds):]
                    
                    # Auto-Gain Control (AGC) Digitale
                    max_val = np.max(np.abs(raw_audio))
                    if max_val > 0.001:
                        processed_audio = (raw_audio / max_val) * 0.9
                    else:
                        processed_audio = raw_audio
                        
                    # 3. Trascrizione Dinamica
                    beam_size = int(self.settings.get("beam_size", 5))
                    vad_on = self.settings.get("vad_filter", True)
                    vad_thresh = float(self.settings.get("vad_threshold", 0.4))
                    rep_penalty = float(self.settings.get("repetition_penalty", 1.2))
                    
                    user_prompt = self.settings.get("initial_prompt", "trascrizione in minuscolo senza punteggiatura.")
                    if self.settings.get("no_censorship", False):
                        user_prompt += " parolacce permesse."
                    
                    segments, _ = self.model_v3.transcribe(
                        processed_audio, 
                        language="it",
                        beam_size=beam_size,
                        best_of=beam_size if beam_size > 1 else 1,
                        temperature=0,
                        repetition_penalty=rep_penalty,
                        vad_filter=vad_on,
                        vad_parameters=dict(min_speech_duration_ms=300, threshold=vad_thresh),
                        initial_prompt=user_prompt
                    )
                    
                    # Facciamo girare gli altri in background per saturare l'hardware se presenti
                    if self.model_v2:
                        _ = self.model_v2.transcribe(processed_audio, language="it", beam_size=1)
                    if self.model_cpu:
                        _ = self.model_cpu.transcribe(processed_audio, language="it", beam_size=1)
                    
                    import re
                    new_words = []
                    blacklist = ["sottotitoli", "grazie", "visione", "iscrivetevi", "canale", "prossimo", "video"]
                    
                    force_lower = self.settings.get("force_lowercase", True)
                    no_punct = self.settings.get("no_punctuation", True)

                    for segment in segments:
                        seg_text = segment.text.strip()
                        if force_lower:
                            seg_text = seg_text.lower()
                            
                        if any(b in seg_text for b in ["grazie per la visione", "sottotitoli"]):
                            continue
                            
                        words = seg_text.split()
                        for w in words:
                            if no_punct:
                                w = re.sub(r'[^\w\s]', '', w).strip()
                            
                            if force_lower:
                                w = w.lower()
                                
                            if w in blacklist or not w:
                                continue
                            new_words.append(w)
                    
                    if new_words:
                        # --- LOGICA DI OVERLAP (Per finestra da 5s) ---
                        history = self.last_display_text.split()
                        start_index = 0
                        
                        # Cerchiamo l'ancora (ultime 3 parole della storia)
                        if len(history) >= 2:
                            for i in range(len(new_words) - 1):
                                # Se troviamo 2 parole consecutive che coincidono con la fine della storia
                                if new_words[i:i+2] == history[-2:]:
                                    start_index = i + 2
                                    break
                                elif new_words[i:i+1] == history[-1:]:
                                    start_index = i + 1
                                    # Non break, cerchiamo se c'è un match migliore (2 parole)
                        
                        truly_new = new_words[start_index:]
                        if truly_new:
                            logger.info(f"New words: {' '.join(truly_new)}")
                            full_list = history + truly_new
                            # Mostriamo le ultime 12 parole per non riempire lo schermo
                            display_text = " ".join(full_list[-12:])
                            
                            if display_text != self.last_display_text:
                                self.result_callback(display_text)
                                self.last_display_text = display_text
                    else:
                        pass
                
                time.sleep(0.1)
            except Exception as e:
                print(f"Transcription error: {e}")
                time.sleep(1)

    def stop(self):
        self.running = False
