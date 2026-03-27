#!/usr/bin/env python3
"""
Clipboard TTS tool.
Press Ctrl+Option+V to read the current clipboard text aloud using Google Cloud TTS.
Audio is also saved as an MP3 to the Desktop for future playback.

Requires:
  export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
  pip3 install pynput google-cloud-texttospeech
"""

import os
import subprocess
import threading
import datetime
from pynput import keyboard
from google.cloud import texttospeech

# WaveNet voice — change to e.g. "en-US-Neural2-C" for a Neural2 voice
LANGUAGE_CODE = "en-US"
VOICE_NAME = "en-US-Wavenet-F"
AUDIO_ENCODING = texttospeech.AudioEncoding.MP3
DESKTOP = os.path.expanduser("~/Desktop/TTS Recordings")
os.makedirs(DESKTOP, exist_ok=True)

tts_lock = threading.Lock()
pressed_keys = set()


def notify(title, message):
    subprocess.run([
        "osascript", "-e",
        f'display notification "{message}" with title "{title}"'
    ])


def get_clipboard():
    result = subprocess.run("pbpaste", capture_output=True)
    return result.stdout.decode("utf-8", errors="replace").strip()


def speak_clipboard():
    text = get_clipboard()
    if not text:
        notify("TTS Clipboard", "Clipboard is empty.")
        print("Clipboard is empty.")
        return

    preview = text[:60] + ("..." if len(text) > 60 else "")
    notify("TTS Clipboard", f"Speaking: {preview}")
    print(f"Speaking: {preview}")

    try:
        client = texttospeech.TextToSpeechClient()

        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code=LANGUAGE_CODE,
            name=VOICE_NAME,
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=AUDIO_ENCODING,
        )

        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_path = os.path.join(DESKTOP, f"tts_{timestamp}.mp3")

        with open(output_path, "wb") as f:
            f.write(response.audio_content)

        print(f"Saved to {output_path}")

        # Play the audio (afplay is built-in on macOS)
        subprocess.Popen(["afplay", output_path])

        notify("TTS Clipboard", f"Saved to Desktop: tts_{timestamp}.mp3")

    except Exception as e:
        notify("TTS Clipboard", f"Error: {e}")
        print(f"Error: {e}")


def on_press(key):
    pressed_keys.add(key)
    ctrl = keyboard.Key.ctrl
    alt = keyboard.Key.alt
    try:
        v = keyboard.KeyCode.from_char('v')
    except Exception:
        return

    if ctrl in pressed_keys and alt in pressed_keys and v in pressed_keys:
        with tts_lock:
            threading.Thread(target=speak_clipboard, daemon=True).start()


def on_release(key):
    pressed_keys.discard(key)


print("TTS Clipboard running. Press Ctrl+Option+V to speak clipboard text. Ctrl+C to quit.")

with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()
