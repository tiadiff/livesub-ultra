from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QApplication, 
                             QPushButton, QFrame, QSystemTrayIcon, QMenu, QStyle, 
                             QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox, QFormLayout, 
                             QDialog, QGroupBox, QScrollArea, QLineEdit)
from PyQt6.QtGui import QIcon, QAction, QColor
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
import json
import os
import pyaudiowpatch as pyaudio

class SubtitleSignal(QObject):
    update_text = pyqtSignal(str)
    update_status = pyqtSignal(str)
    settings_changed = pyqtSignal(dict)

class OverlayWindow(QWidget):
    def __init__(self, signal_bus=None):
        super().__init__()
        self.signal_bus = signal_bus
        self.settings_path = "settings.json"
        self.load_settings()
        self.initUI()
        self.setupTrayIcon()
        self.settings_window = None
        
    def load_settings(self):
        default_settings = {
            "font_size": 36,
            "opacity": 220,
            "window_width": 1100,
            "window_height": 250,
            "model_size": "large-v3-turbo",
            "device": "auto",
            "compute_type": "auto",
            "use_stacking": False,
            "audio_device_index": -1
        }
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r') as f:
                    self.settings = json.load(f)
            except:
                self.settings = default_settings
        else:
            self.settings = default_settings
            self.save_settings()

    def save_settings(self):
        try:
            with open(self.settings_path, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")
        
    def initUI(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Window |
            Qt.WindowType.Tool
        )
        self.setWindowTitle("LiveSub Ultra")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # One-time UI creation
        self.setup_ui_elements()
        self.update_window_geometry()
        
    def setup_ui_elements(self):
        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Subtitle Label
        self.label = QLabel("LiveSub Ultra: Avvio sistema...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.label.setWordWrap(True)
        self.main_layout.addWidget(self.label)
        
        self.clear_timer = QTimer()
        self.clear_timer.setSingleShot(True)
        self.clear_timer.timeout.connect(self.hide_text)
        
        # Static Block System
        self.word_queue = []
        self.current_display_words = []
        self.is_frozen = False 
        self.pacing_timer = QTimer()
        self.pacing_timer.timeout.connect(self._process_word_queue)
        self.pacing_timer.start(80)

    def update_window_geometry(self):
        self.width_pref = self.settings.get("window_width", 1100)
        font_size = self.settings.get("font_size", 36)
        # Altezza proporzionata: 2 righe + padding
        self.max_height = int(font_size * 2.5) + 20 
        self.setFixedSize(self.width_pref, self.max_height)
        
        # Screen positioning (bottom center)
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - self.width_pref) // 2,
            screen.height() - self.max_height - 80
        )
        
        self.setMinimumSize(400, 50)
        self.setMaximumSize(1920, 1080)
        self.apply_style()
        self.show()

    def apply_style(self):
        size = self.settings.get("font_size", 36)
        self.label.setStyleSheet(f"""
            QLabel {{
                color: #FFFFFF;
                background-color: rgba(10, 10, 10, 245);
                border: 2px solid rgba(255, 255, 255, 60);
                border-radius: 10px;
                padding: 5px 20px;
                font-family: 'Segoe UI', 'Inter', sans-serif;
                font-size: {size}px;
                font-weight: 700;
                line-height: 1.1;
            }}
        """)

    def setupTrayIcon(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        # Carica l'icona
        icon_path = "icon.png"
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            # Fallback a un'icona di sistema se non trovata
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
            
        # Menu contestuale per la Tray
        tray_menu = QMenu()
        tray_menu.setStyleSheet("background-color: #222; color: white; border: 1px solid #444;")
        
        title_action = QAction("LiveSub Ultra", self)
        title_action.setEnabled(False)
        tray_menu.addAction(title_action)
        tray_menu.addSeparator()
        
        settings_action = tray_menu.addAction("Impostazioni")
        settings_action.triggered.connect(self.open_settings)
        
        inc_font = tray_menu.addAction("Aumenta Font (+4)")
        dec_font = tray_menu.addAction("Diminuisci Font (-4)")
        inc_font.triggered.connect(lambda: self.adjust_font(4))
        dec_font.triggered.connect(lambda: self.adjust_font(-4))
        
        tray_menu.addSeparator()
        
        toggle_action = tray_menu.addAction("Mostra/Nascondi")
        toggle_action.triggered.connect(self.toggle_window)
        
        exit_action = tray_menu.addAction("Esci")
        exit_action.triggered.connect(self.close_app)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        # Click sull'icona mostra/nasconde
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_window()

    def toggle_window(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()

    def adjust_font(self, delta):
        self.settings["font_size"] = max(12, min(72, self.settings.get("font_size", 36) + delta))
        self.update_window_geometry()
        self.apply_style()
        self.save_settings()

    def open_settings(self):
        if self.settings_window is None:
            self.settings_window = SettingsWindow(self.settings, self.on_settings_saved)
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def on_settings_saved(self, new_settings):
        self.settings = new_settings
        self.save_settings()
        self.update_window_geometry()
        self.apply_style()
        if self.signal_bus:
            self.signal_bus.settings_changed.emit(self.settings)

    def update_subtitle(self, text):
        if not text.strip():
            self.word_queue = []
            self.current_display_words = []
            self.label.setText("")
            return
            
        new_words = text.split()
        for w in new_words:
            if w not in self.current_display_words and w not in self.word_queue:
                self.word_queue.append(w)
        
        self.clear_timer.start(10000)

    def _process_word_queue(self):
        if not self.word_queue or self.is_frozen:
            return
            
        # Se il box è pieno (max 12 parole), lo svuotiamo per rimanere su 1-2 righe
        if len(self.current_display_words) > 12:
            self.is_frozen = True
            # Aspettiamo 800ms prima di pulire e riprendere
            QTimer.singleShot(800, self._clear_and_unfreeze)
            return

        next_word = self.word_queue.pop(0)
        self.current_display_words.append(next_word)
        self.label.setText(" ".join(self.current_display_words))

    def _clear_and_unfreeze(self):
        self.current_display_words = []
        self.label.setText("")
        self.is_frozen = False

    def update_status(self, text):
        """Show non-transcription system messages"""
        self.label.setText(f"<i style='color: #AAA; font-size: 0.8em;'>{text}</i>")

    def contextMenuEvent(self, event):
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet("background-color: #222; color: white; border: 1px solid #444;")
        inc_font = menu.addAction("Aumenta Font (+4)")
        dec_font = menu.addAction("Diminuisci Font (-4)")
        menu.addSeparator()
        settings_action = menu.addAction("Impostazioni")
        hide_action = menu.addAction("Nascondi (Tray)")
        close_action = menu.addAction("Esci")
        
        action = menu.exec(event.globalPos())
        if action == inc_font:
            self.adjust_font(4)
        elif action == dec_font:
            self.adjust_font(-4)
        elif action == settings_action:
            self.open_settings()
        elif action == hide_action:
            self.hide()
        elif action == close_action:
            self.close_app()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragPos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(self.pos() + event.globalPosition().toPoint() - self.dragPos)
            self.dragPos = event.globalPosition().toPoint()
            event.accept()

    def close_app(self):
        QApplication.quit()

    def hide_text(self):
        self.label.setText("")

class SettingsWindow(QDialog):
    def __init__(self, current_settings, save_callback):
        super().__init__()
        self.current_settings = current_settings.copy()
        self.save_callback = save_callback
        self.setWindowTitle("Impostazioni LiveSub Ultra")
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog { background-color: #1a1a1a; color: white; }
            QLabel { color: #ccc; }
            .help-text { color: #888; font-size: 10px; margin-bottom: 5px; }
            QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit { 
                background-color: #333; color: white; border: 1px solid #444; 
                padding: 4px; border-radius: 4px;
                min-height: 25px;
            }
            QSpinBox::up-button, QDoubleSpinBox::up-button {
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 20px; border-left: 1px solid #444;
            }
            QSpinBox::down-button, QDoubleSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 20px; border-left: 1px solid #444;
            }
            QPushButton { 
                background-color: #444; color: white; border: none; 
                padding: 8px 15px; border-radius: 4px; 
            }
            QPushButton:hover { background-color: #555; }
            QGroupBox { 
                color: #fff; font-weight: bold; border: 1px solid #444; 
                margin-top: 1.5em; border-radius: 5px; padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 5px;
            }
            QCheckBox { color: #ccc; }
            QScrollArea { border: none; background-color: transparent; }
        """)
        self.initUI()

    def addRowWithHelp(self, layout, label_text, widget, help_text):
        label = QLabel(label_text)
        layout.addRow(label, widget)
        help_label = QLabel(help_text)
        help_label.setProperty("class", "help-text")
        help_label.setWordWrap(True)
        layout.addRow("", help_label)

    def initUI(self):
        main_layout = QVBoxLayout(self)
        self.setMinimumHeight(600)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        # UI Group
        ui_group = QGroupBox("Interfaccia")
        ui_layout = QFormLayout()
        
        self.font_size = QSpinBox()
        self.font_size.setRange(12, 120)
        self.font_size.setValue(self.current_settings.get("font_size", 36))
        self.addRowWithHelp(ui_layout, "Dimensione Font:", self.font_size, "Grandezza del testo dei sottotitoli.")
        
        self.win_width = QSpinBox()
        self.win_width.setRange(400, 3840)
        self.win_width.setValue(self.current_settings.get("window_width", 1100))
        self.addRowWithHelp(ui_layout, "Larghezza Finestra:", self.win_width, "Larghezza massima dell'area sottotitoli.")
        
        ui_group.setLayout(ui_layout)
        layout.addWidget(ui_group)

        # AI Group
        ai_group = QGroupBox("Motore IA (Whisper)")
        ai_layout = QFormLayout()

        self.model_size = QComboBox()
        self.model_size.addItems(["tiny", "base", "small", "medium", "large-v2", "large-v3", "large-v3-turbo"])
        self.model_size.setCurrentText(self.current_settings.get("model_size", "large-v3-turbo"))
        self.addRowWithHelp(ai_layout, "Modello:", self.model_size, "Più è grande, più è preciso ma lento (Large è il top).")

        self.device = QComboBox()
        self.device.addItems(["auto", "cuda", "cpu"])
        self.device.setCurrentText(self.current_settings.get("device", "auto"))
        self.addRowWithHelp(ai_layout, "Dispositivo:", self.device, "Usa CUDA se hai una scheda NVIDIA per massima velocità.")

        self.compute_type = QComboBox()
        self.compute_type.addItems(["auto", "float16", "int8", "float32"])
        self.compute_type.setCurrentText(self.current_settings.get("compute_type", "auto"))
        self.addRowWithHelp(ai_layout, "Precisione:", self.compute_type, "Float32 è la massima qualità, Float16 è il miglior compromesso.")

        self.beam_size = QSpinBox()
        self.beam_size.setRange(1, 15)
        self.beam_size.setValue(self.current_settings.get("beam_size", 5))
        self.addRowWithHelp(ai_layout, "Beam Size:", self.beam_size, "Profondità di analisi. 1 è istantaneo, 5 è professionale.")

        self.repetition_penalty = QDoubleSpinBox()
        self.repetition_penalty.setRange(1.0, 2.0)
        self.repetition_penalty.setSingleStep(0.1)
        self.repetition_penalty.setValue(self.current_settings.get("repetition_penalty", 1.2))
        self.addRowWithHelp(ai_layout, "Penalità Ripetizione:", self.repetition_penalty, "Evita che l'IA ripeta le stesse parole in loop.")

        ai_group.setLayout(ai_layout)
        layout.addWidget(ai_group)

        # Transcription Group
        trans_group = QGroupBox("Stile e Comportamento")
        trans_layout = QFormLayout()

        self.context_window = QComboBox()
        self.context_window.addItems(["2.5", "3.0", "4.0", "5.0", "7.5", "10.0"])
        self.context_window.setCurrentText(str(self.current_settings.get("context_window", 5.0)))
        self.addRowWithHelp(trans_layout, "Finestra Contesto (sec):", self.context_window, "Quanto audio 'passato' l'IA può riascoltare per capire la frase.")

        self.vad_filter = QCheckBox("Filtro Voce (VAD)")
        self.vad_filter.setChecked(self.current_settings.get("vad_filter", True))
        self.addRowWithHelp(trans_layout, "VAD Filter:", self.vad_filter, "Ignora i silenzi e i rumori non umani.")

        self.vad_threshold = QDoubleSpinBox()
        self.vad_threshold.setRange(0.1, 0.9)
        self.vad_threshold.setSingleStep(0.05)
        self.vad_threshold.setValue(self.current_settings.get("vad_threshold", 0.4))
        self.addRowWithHelp(trans_layout, "Soglia Voce:", self.vad_threshold, "Quanto deve essere chiara la voce per attivarsi (0.4 consigliato).")

        self.force_lowercase = QCheckBox("Tutto Minuscolo")
        self.force_lowercase.setChecked(self.current_settings.get("force_lowercase", True))
        trans_layout.addRow(self.force_lowercase)

        self.no_punctuation = QCheckBox("Niente Punteggiatura")
        self.no_punctuation.setChecked(self.current_settings.get("no_punctuation", True))
        trans_layout.addRow(self.no_punctuation)

        self.no_censorship = QCheckBox("Disattiva Filtro Imprecazioni")
        self.no_censorship.setChecked(self.current_settings.get("no_censorship", True))
        self.addRowWithHelp(trans_layout, "No Censura:", self.no_censorship, "Permette la trascrizione fedele di parolacce e termini volgari.")

        self.initial_prompt = QLineEdit()
        self.initial_prompt.setText(self.current_settings.get("initial_prompt", "trascrizione in minuscolo senza punteggiatura."))
        self.addRowWithHelp(trans_layout, "Prompt IA:", self.initial_prompt, "Istruzioni per l'IA (es. 'usa termini tecnici', 'traducimi in inglese').")

        trans_group.setLayout(trans_layout)
        layout.addWidget(trans_group)

        # Audio Group
        audio_group = QGroupBox("Audio")
        audio_layout = QFormLayout()
        
        self.audio_device = QComboBox()
        self.populate_audio_devices()
        self.addRowWithHelp(audio_layout, "Sorgente Audio:", self.audio_device, "Il dispositivo da cui 'ascoltare' l'audio di sistema.")
        
        audio_group.setLayout(audio_layout)
        layout.addWidget(audio_group)

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Salva e Applica")
        save_btn.clicked.connect(self.save)
        save_btn.setStyleSheet("background-color: #0078d4; font-weight: bold;")
        
        cancel_btn = QPushButton("Annulla")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        main_layout.addLayout(btn_layout)

    def populate_audio_devices(self):
        self.audio_device.addItem("Default (Loopback)", -1)
        try:
            p = pyaudio.PyAudio()
            # Mostra solo dispositivi WASAPI per loopback su Windows
            wasapi_idx = -1
            for i in range(p.get_host_api_count()):
                if "WASAPI" in p.get_host_api_info_by_index(i)["name"]:
                    wasapi_idx = i
                    break
            
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if wasapi_idx != -1 and info["hostApi"] != wasapi_idx:
                    continue
                name = info["name"]
                # Aggiungi indicazione se è un dispositivo di output (per loopback)
                if info["maxOutputChannels"] > 0:
                    self.audio_device.addItem(f"{name} [Output]", i)
                elif info["maxInputChannels"] > 0:
                    self.audio_device.addItem(f"{name} [Input]", i)
            p.terminate()
            
            # Seleziona quello corrente
            idx = self.current_settings.get("audio_device_index", -1)
            for i in range(self.audio_device.count()):
                if self.audio_device.itemData(i) == idx:
                    self.audio_device.setCurrentIndex(i)
                    break
        except Exception as e:
            print(f"Error listing audio devices: {e}")

    def save(self):
        new_settings = {
            "font_size": self.font_size.value(),
            "window_width": self.win_width.value(),
            "model_size": self.model_size.currentText(),
            "device": self.device.currentText(),
            "compute_type": self.compute_type.currentText(),
            "audio_device_index": self.audio_device.currentData(),
            "beam_size": self.beam_size.value(),
            "repetition_penalty": self.repetition_penalty.value(),
            "vad_filter": self.vad_filter.isChecked(),
            "vad_threshold": self.vad_threshold.value(),
            "context_window": float(self.context_window.currentText()),
            "force_lowercase": self.force_lowercase.isChecked(),
            "no_punctuation": self.no_punctuation.isChecked(),
            "no_censorship": self.no_censorship.isChecked(),
            "initial_prompt": self.initial_prompt.text(),
            "opacity": self.current_settings.get("opacity", 220),
            "window_height": self.current_settings.get("window_height", 250),
            "use_stacking": self.current_settings.get("use_stacking", False)
        }
        self.save_callback(new_settings)
        self.accept()
