from faster_whisper import WhisperModel
import threading
import numpy as np
import os
import sys
import queue
import time

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
            if use_stacking:
                # 1. PRIMARY GPU (Float16)
                self.status_callback(f"Caricamento {model_size} (GPU, {compute_type})...")
                self.model_v3 = WhisperModel(
                    model_size, 
                    device=device, 
                    compute_type=compute_type,
                    num_workers=2
                )
                
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
                self.model_v3 = WhisperModel(
                    model_size, 
                    device=device, 
                    compute_type=compute_type
                )
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
                    # 2. Pre-elaborazione Leggera (Noise reduction)
                    raw_audio = np.array(self.buffer, dtype=np.float32)[-int(self.sample_rate * 2.5):]
                    
                    max_val = np.max(np.abs(raw_audio))
                    if max_val > 0.01:
                        processed_audio = raw_audio / max_val
                    else:
                        processed_audio = raw_audio
                        
                    # 3. Trascrizione Triple-Engine (Massimo Carico)
                    # Usiamo il V3 come primario, ma facciamo lavorare tutti
                    segments, _ = self.model_v3.transcribe(
                        processed_audio, 
                        language="it",
                        beam_size=5,
                        best_of=3,
                        temperature=0,
                        word_timestamps=True,
                        condition_on_previous_text=False,
                        repetition_penalty=1.2,
                        no_repeat_ngram_size=3,
                        vad_filter=True,
                        vad_parameters=dict(min_speech_duration_ms=250),
                        initial_prompt="Trascrizione veloce, solo testo, niente punteggiatura."
                    )
                    
                    # Facciamo girare gli altri in background per saturare l'hardware se presenti
                    if self.model_v2:
                        _ = self.model_v2.transcribe(processed_audio, language="it", beam_size=1)
                    if self.model_cpu:
                        _ = self.model_cpu.transcribe(processed_audio, language="it", beam_size=1)
                    
                    new_words = []
                    blacklist = [
                        "grazie", "iscrivetevi", "canale", "sottotitoli", 
                        "visione", "guardato", "prossimo video"
                    ]
                    
                    for segment in segments:
                        # Se il segmento intero puzza di allucinazione (troppo corto o frasi fatte)
                        seg_text = segment.text.lower().strip()
                        if any(b in seg_text for b in ["iscrivetevi al canale", "grazie per la visione"]):
                            continue
                            
                        if segment.words:
                            for word in segment.words:
                                import re
                                w = word.word.strip().lower()
                                w = re.sub(r'[^\w\s]', '', w)
                                
                                # Filtro parole singole della blacklist solo se sospette
                                if w in blacklist and len(segment.words) < 3:
                                    continue
                                if w: new_words.append(w)
                    
                    if len(new_words) > 2:
                        # Safety margin: non mostriamo l'ultima parola
                        current_ai_words = new_words[:-1]
                        
                        # Recuperiamo la storia recente (ultime 10 parole mostrate)
                        history = self.last_display_text.split()
                        
                        # LOGICA OVERLAP: Cerchiamo dove la nuova trascrizione si aggancia alla storia
                        # Proviamo a far combaciare le ultime 2 o 3 parole della storia
                        start_index = 0
                        if len(history) >= 2:
                            anchor = history[-2:] # Ultime 2 parole mostrate
                            # Cerchiamo l'ancora nella nuova trascrizione
                            for i in range(len(current_ai_words) - 1):
                                if current_ai_words[i:i+2] == anchor:
                                    start_index = i + 2
                                    break
                        
                        # Prendiamo solo quello che viene DOPO l'ancora
                        words_to_add = current_ai_words[start_index:]
                        
                        if words_to_add:
                            # Aggiorniamo il testo aggiungendo solo il nuovo
                            full_text_list = history + words_to_add
                            # Teniamo solo le ultime 10 parole per pulizia UI
                            display_text = " ".join(full_text_list[-10:])
                            
                            if display_text != self.last_display_text:
                                self.result_callback(display_text)
                                self.last_display_text = display_text
                
                time.sleep(0.1)
            except Exception as e:
                print(f"Transcription error: {e}")
                time.sleep(1)

    def stop(self):
        self.running = False
