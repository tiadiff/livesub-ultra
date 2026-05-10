from faster_whisper import WhisperModel
import numpy as np

def test():
    print("Testing Whisper Model Loading...")
    try:
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        print("Model loaded successfully!")
        
        # Create a tiny silent audio
        audio = np.zeros(16000, dtype=np.float32)
        segments, info = model.transcribe(audio, language="en")
        list(segments) # Trigger processing
        print("Transcription test successful!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
