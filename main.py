import sys
import os
import time

# --- FIX NVIDIA CUDA DLLs ---
if sys.platform == 'win32':
    # Support for PyInstaller bundled DLLs
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        nvidia_root = os.path.join(base_path, 'nvidia')
        if os.path.exists(nvidia_root):
            for sub in os.listdir(nvidia_root):
                bin_dir = os.path.join(nvidia_root, sub, 'bin')
                if os.path.exists(bin_dir):
                    os.add_dll_directory(bin_dir)
                    os.environ["PATH"] = bin_dir + os.pathsep + os.environ["PATH"]
    
    # Support for standard pip installation
    for path in sys.path:
        if 'site-packages' in path:
            for lib in ['cublas', 'cudnn', 'cublas_cu12', 'cudnn_cu12']:
                lib_path = os.path.join(path, 'nvidia', lib, 'bin')
                if os.path.exists(lib_path):
                    if hasattr(os, "add_dll_directory"):
                        os.add_dll_directory(lib_path)
                    os.environ["PATH"] = lib_path + os.pathsep + os.environ["PATH"]

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
        settings = self.window.settings
        
        # Audio Capture
        device_idx = settings.get("audio_device_index", -1)
        self.audio_capture = AudioCapture(device_index=device_idx)
        self.audio_capture.start()
        
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
        print("Restarting services now...")
        self.stop_services()
        self.start_services()

    def run(self):
        try:
            sys.exit(self.app.exec())
        finally:
            self.stop_services()

def main():
    print("--- LiveSub v1.2 ---")
    app_instance = LiveSubApp()
    app_instance.run()

if __name__ == "__main__":
    main()
