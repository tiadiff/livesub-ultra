# 🎙️ LiveSub Ultra

LiveSub Ultra is a high-performance, real-time **AI subtitle generator** designed to capture system audio and display instant transcriptions. Powered by OpenAI's Whisper (via `faster-whisper`), it provides highly accurate, low-latency subtitles directly on your screen.

![LiveSub Banner](https://img.shields.io/badge/AI-Whisper-blue?style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?style=for-the-badge&logo=windows)

---

## 🚀 Key Features

- **Extreme Performance**: Optional "Triple-Stack" mode runs 3 AI models simultaneously for maximum accuracy on high-end hardware.
- **Sleek Overlay**: A semi-transparent, frameless window that stays on top of other applications.
- **System Tray Integration**: Runs discreetly in the notification area to keep your taskbar clean.
- **Loopback Audio**: Directly captures audio from videos, games, or calls (WASAPI Loopback) without extra hardware.
- **Fully Configurable**: Easily change models, hardware acceleration (CUDA/CPU), and audio sources via the built-in Settings panel.

---

## 📖 How to Use

### 🖱️ Controls & Interaction
- **Drag & Move**: Left-click and drag the subtitle overlay to position it anywhere on your screen.
- **Right-Click (Overlay)**: Opens a quick menu to:
  - Increase/Decrease font size.
  - Open the **Settings** panel.
  - Hide the overlay (minimizes to System Tray).
  - Exit the application.
- **System Tray Icon**: 
  - **Single Click**: Instantly toggle visibility (Show/Hide) of the subtitles.
  - **Right-Click**: Access the full control menu (Settings, Font size, Exit).

### ⚙️ Settings Panel
Accessible via the right-click menu, the Settings panel allows you to:
1. **AI Model**: Choose from `tiny`, `base`, `small`, `medium`, `large-v3`, or `large-v3-turbo`.
2. **Hardware Acceleration**: Select `CUDA` (NVIDIA GPU), `CPU`, or `Auto`.
3. **Compute Type**: Adjust precision (`float16`, `int8`, `float32`).
4. **Performance Mode**: Enable **Triple-Stacking** to run multiple models at once (Recommended for RTX 30/40 series GPUs).
5. **Audio Source**: Select which output device to listen to.

---

## 🛠️ Installation

### Requirements
- **Windows 10/11**
- **Python 3.10+**
- **FFmpeg**: Required for audio processing (must be in your system PATH).
- **NVIDIA GPU** (Optional): Highly recommended for `large` models and performance modes.

### Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/tiadiff/-livesub-ultra.git
   cd livesub-ultra
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the App
```bash
python main.py
```

---

## 📝 License
Distributed under the MIT License. See `LICENSE` for more information.

---
*Developed with ❤️ to make audio accessible to everyone.*
