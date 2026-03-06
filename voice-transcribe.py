#!/usr/bin/env python3
"""
Voice transcription tool.
Press Ctrl+Option+V to start recording, press again to stop.
Audio is transcribed via Voxtral and copied to clipboard.

Set your Mistral API key in a .env file or as an environment variable:
  export MISTRAL_API_KEY=your_key_here
"""

import os
import subprocess
import tempfile
import threading
import requests
from pynput import keyboard

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")
MODEL = "voxtral-mini-latest"
ENDPOINT = "https://api.mistral.ai/v1/audio/transcriptions"

if not MISTRAL_API_KEY:
    raise SystemExit("Error: MISTRAL_API_KEY environment variable not set. See README for setup instructions.")

recording_process = None
recording_lock = threading.Lock()
temp_file = None


def notify(title, message):
    subprocess.run([
        "osascript", "-e",
        f'display notification "{message}" with title "{title}"'
    ])


def start_recording():
    global recording_process, temp_file
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_file = tmp.name
    tmp.close()
    recording_process = subprocess.Popen([
        "/opt/homebrew/bin/sox", "-d", "-r", "16000", "-c", "1", "-b", "16", temp_file
    ], stderr=subprocess.DEVNULL)
    notify("Voice Transcribe", "Recording...")
    print("Recording started...")


def stop_and_transcribe():
    global recording_process, temp_file
    recording_process.terminate()
    recording_process.wait()
    recording_process = None
    notify("Voice Transcribe", "Transcribing...")
    print("Recording stopped. Transcribing...")

    audio_path = temp_file
    temp_file = None

    threading.Thread(target=transcribe, args=(audio_path,), daemon=True).start()


def transcribe(audio_path):
    try:
        with open(audio_path, "rb") as f:
            response = requests.post(
                ENDPOINT,
                headers={"Authorization": f"Bearer {MISTRAL_API_KEY}"},
                files={"file": ("audio.wav", f, "audio/wav")},
                data={"model": MODEL},
                timeout=60
            )
        response.raise_for_status()
        text = response.json().get("text", "").strip()
        if text:
            subprocess.run("pbcopy", input=text.encode(), check=True)
            notify("Voice Transcribe", f"Copied: {text[:60]}{'...' if len(text) > 60 else ''}")
            print(f"Copied to clipboard: {text}")
        else:
            notify("Voice Transcribe", "No speech detected.")
            print("No speech detected.")
    except Exception as e:
        notify("Voice Transcribe", f"Error: {e}")
        print(f"Error: {e}")
    finally:
        try:
            os.unlink(audio_path)
        except Exception:
            pass


pressed_keys = set()


def on_press(key):
    pressed_keys.add(key)
    ctrl = keyboard.Key.ctrl
    alt = keyboard.Key.alt
    try:
        v = keyboard.KeyCode.from_char('v')
    except Exception:
        return

    if ctrl in pressed_keys and alt in pressed_keys and v in pressed_keys:
        with recording_lock:
            if recording_process is None:
                start_recording()
            else:
                stop_and_transcribe()


def on_release(key):
    pressed_keys.discard(key)


print("Voice transcribe running. Press Ctrl+Option+V to toggle recording. Ctrl+C to quit.")

with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()
