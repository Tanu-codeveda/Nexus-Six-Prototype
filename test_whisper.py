import whisper
import warnings
import os
import urllib.request

# Suppress some harmless warnings from Whisper
warnings.filterwarnings("ignore")

print("1. Loading Whisper model ('tiny')...")
# 'tiny' is the smallest model, good for a quick test to see if everything works.
model = whisper.load_model("tiny")
print("Model loaded successfully!")

# Download a sample audio file for testing
audio_file = "sample.wav"
if not os.path.exists(audio_file):
    print(f"Downloading a sample audio file ({audio_file})...")
    # A short, public domain speech sample
    url = "https://www2.cs.uic.edu/~i101/SoundFiles/preamble10.wav"
    try:
        urllib.request.urlretrieve(url, audio_file)
    except Exception as e:
        print(f"Failed to download sample audio. Please provide your own audio file named '{audio_file}'. Error: {e}")
        exit(1)

print(f"\n2. Transcribing '{audio_file}'...")
print("(This proves that FFmpeg and PyTorch are working together!)")
try:
    result = model.transcribe(audio_file)
    print("\n--- Transcription Result ---")
    print(result["text"].strip())
    print("----------------------------\n")
    print("✅ Success! Whisper is fully operational on your device.")
except Exception as e:
    print(f"\n❌ An error occurred during transcription: {e}")
