import sys
import os
import time
import logging

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LiveSub")
logger.info("--- LiveSub Ultra Starting ---")

# --- FIX NVIDIA CUDA DLLs ---
if sys.platform == 'win32':
    try:
        # Support for PyInstaller bundled DLLs
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
            nvidia_root = os.path.join(base_path, 'nvidia')
            if os.path.exists(nvidia_root):
                for sub in os.listdir(nvidia_root):
                    bin_dir = os.path.join(nvidia_root, sub, 'bin')
                    if os.path.exists(bin_dir):
                        try:
                            os.add_dll_directory(bin_dir)
                            os.environ["PATH"] = bin_dir + os.pathsep + os.environ["PATH"]
                        except Exception:
                            pass
        
        # Support for standard pip installation
        for path in sys.path:
            if 'site-packages' in path:
                for lib in ['cublas', 'cudnn', 'cublas_cu12', 'cudnn_cu12']:
                    lib_path = os.path.join(path, 'nvidia', lib, 'bin')
                    if os.path.exists(lib_path):
                        try:
                            if hasattr(os, "add_dll_directory"):
                                os.add_dll_directory(lib_path)
                            os.environ["PATH"] = lib_path + os.pathsep + os.environ["PATH"]
                        except Exception:
                            pass
    except Exception as e:
        print(f"DLL Load Warning: {e}")

from PyQt6.QtWidgets import QApplication
from audio_capture import AudioCapture
from transcription import TranscriptionWorker
from ui import OverlayWindow, SubtitleSignal

class LiveSubApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.signal_bus = SubtitleSignal()
        
        # UI Setup
        self.window = OverlayWindow(signal_bus=self.signal_bus)
        self.signal_bus.update_text.connect(self.window.update_subtitle)
        self.signal_bus.update_status.connect(self.window.update_status)
        self.signal_bus.settings_changed.connect(self.restart_services)
        
        self.audio_capture = None
        self.transcriber = None
        
        self.start_services()

    def start_services(self):
        self.signal_bus.update_status.emit("Inizializzazione in corso...")
        settings = self.window.settings
        
        # Audio Capture
        device_idx = settings.get("audio_device_index", -1)
        self.audio_capture = AudioCapture(device_index=device_idx)
        self.audio_capture.start()
        
        self.signal_bus.update_status.emit("Caricamento Motori IA (Whisper)...")
        
        # Transcription Worker
        self.transcriber = TranscriptionWorker(
            self.audio_capture.audio_queue, 
            lambda text: self.signal_bus.update_text.emit(text),
            lambda status: self.signal_bus.update_status.emit(status),
            settings=settings
        )
        self.transcriber.start()

    def stop_services(self):
        if self.transcriber:
            self.transcriber.stop()
        if self.audio_capture:
            self.audio_capture.stop()
        
        # Wait for threads to finish
        if self.transcriber:
            self.transcriber.join(timeout=2)
        if self.audio_capture:
            self.audio_capture.join(timeout=2)

    def restart_services(self, new_settings):
        # Usiamo un timer per non bloccare la chiusura del dialogo delle impostazioni
        print("Settings changed. Scheduling restart...")
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, self._do_restart)

    def _do_restart(self):
        try:
            print("Restarting services now...")
            self.stop_services()
            # Piccola pausa extra per liberare VRAM
            time.sleep(0.5)
            self.start_services()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self.window, "LiveSub - Errore Riavvio", 
                                f"Impossibile riavviare i servizi:\n\n{e}")
            logger.error(f"Restart failed: {e}")

    def run(self):
        try:
            sys.exit(self.app.exec())
        finally:
            self.stop_services()

def main():
    try:
        print("--- LiveSub v1.2 ---")
        app_instance = LiveSubApp()
        app_instance.run()
    except Exception as e:
        import traceback
        error_msg = f"Errore fatale all'avvio:\n\n{str(e)}\n\n{traceback.format_exc()}"
        print(error_msg)
        try:
            from PyQt6.QtWidgets import QMessageBox, QApplication
            if not QApplication.instance():
                dummy_app = QApplication(sys.argv)
            QMessageBox.critical(None, "LiveSub Ultra - CRASH", error_msg)
        except:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()
