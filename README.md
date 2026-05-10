# 🎙️ LiveSub Ultra

LiveSub Ultra è uno strumento avanzato per la generazione di **sottotitoli in tempo reale** dall'audio di sistema. Utilizza modelli AI all'avanguardia (OpenAI Whisper via `faster-whisper`) per fornire trascrizioni accurate con latenza minima, direttamente sopra le tue applicazioni.

![LiveSub Banner](https://img.shields.io/badge/AI-Whisper-blue?style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?style=for-the-badge&logo=windows)

## ✨ Caratteristiche

- **🚀 Performance Estreme**: Supporto per Triple-Stacking (3 modelli simultanei) per la massima precisione su hardware di fascia alta.
- **🖥️ Overlay Non Invasivo**: Sottotitoli eleganti, semitrasparenti e trascinabili ovunque.
- **⚙️ Pannello Impostazioni**: Configura modello, accelerazione hardware (CUDA/CPU), precisione e sorgente audio direttamente dalla UI.
- **📥 System Tray**: L'app vive nell'area di notifica per non occupare spazio nella barra delle applicazioni.
- **🔊 Loopback Audio**: Cattura l'audio interno (video, chiamate, giochi) senza bisogno di cavi virtuali complessi grazie a WASAPI Loopback.

## 🛠️ Installazione

### Requisiti
- **Windows 10/11**
- **Python 3.10 o superiore**
- **FFmpeg**: Assicurati che sia installato e presente nel PATH.
- **NVIDIA GPU** (Opzionale): Consigliata per modelli `large` e modalità performance.

### Setup Rapido
1. Clona il repository:
   ```bash
   git clone https://github.com/tuo-username/livesub-ultra.git
   cd livesub-ultra
   ```
2. Crea un ambiente virtuale:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. Installa le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Come Usare

Avvia il programma con:
```bash
python main.py
```

### Comandi Rapidi:
- **Tasto Destro sull'Overlay**: Cambia dimensione font, apri impostazioni o chiudi l'app.
- **Tasto Destro sull'Icona Tray**: Mostra/Nascondi sottotitoli o apri le impostazioni.
- **Trascina**: Clicca e trascina i sottotitoli per posizionarli dove preferisci.

## ⚙️ Configurazione

Tramite il pannello **Impostazioni**, puoi adattare LiveSub al tuo PC:
- **Modelli**: Scegli tra `tiny`, `base`, `small`, `medium`, `large-v3` o `large-v3-turbo`.
- **Dispositivo**: Forza `CUDA` per schede NVIDIA o `CPU` per il risparmio energetico.
- **Modalità Performance**: Attiva il "Triple-Stack" per far lavorare più motori IA contemporaneamente e ottenere risultati ultra-precisi.

## 📝 Licenza

Distribuito sotto licenza MIT. Vedi `LICENSE` per maggiori informazioni.

---
*Sviluppato con ❤️ per rendere l'audio accessibile a tutti.*
