#!/usr/bin/env python3
"""
Clipboard TTS tool.
Press Ctrl+Option+V to read the current clipboard text aloud using Google Cloud TTS.
Audio is also saved as an MP3 to the Desktop for future playback.

Long texts are automatically split into chunks and stitched together with ffmpeg.

Requires:
  export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
  pip3 install pynput google-cloud-texttospeech
  brew install ffmpeg
"""

import os
import subprocess
import threading
import datetime
import tempfile
import textwrap
from pynput import keyboard
from google.cloud import texttospeech

# WaveNet voice — change to e.g. "en-US-Neural2-C" for a Neural2 voice
LANGUAGE_CODE = "en-US"
VOICE_NAME = "en-US-Wavenet-F"
AUDIO_ENCODING = texttospeech.AudioEncoding.MP3
DESKTOP = os.path.expanduser("~/Desktop/TTS Recordings")
os.makedirs(DESKTOP, exist_ok=True)

# Google Cloud TTS hard limit is 5000 bytes per request. We chunk conservatively
# at 4800 characters to stay safely under, splitting on sentence boundaries where possible.
CHUNK_SIZE = 4800

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


def split_text(text, chunk_size):
    """Split text into chunks of up to chunk_size characters, breaking on sentence endings."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    while text:
        if len(text) <= chunk_size:
            chunks.append(text)
            break

        # Try to split at a sentence boundary (. ! ?) within the chunk
        segment = text[:chunk_size]
        split_at = max(
            segment.rfind(". "),
            segment.rfind("! "),
            segment.rfind("? "),
            segment.rfind(".\n"),
        )

        if split_at == -1:
            # No sentence boundary found, fall back to splitting on a space
            split_at = segment.rfind(" ")

        if split_at == -1:
            # No space either, hard split
            split_at = chunk_size - 1

        chunks.append(text[:split_at + 1].strip())
        text = text[split_at + 1:].strip()

    return chunks


def synthesize_chunk(client, text, voice, audio_config):
    synthesis_input = texttospeech.SynthesisInput(text=text)
    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config,
    )
    return response.audio_content


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
        voice = texttospeech.VoiceSelectionParams(
            language_code=LANGUAGE_CODE,
            name=VOICE_NAME,
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=AUDIO_ENCODING,
        )

        chunks = split_text(text, CHUNK_SIZE)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_path = os.path.join(DESKTOP, f"tts_{timestamp}.mp3")

        if len(chunks) == 1:
            audio_content = synthesize_chunk(client, chunks[0], voice, audio_config)
            with open(output_path, "wb") as f:
                f.write(audio_content)
        else:
            print(f"Text is long, splitting into {len(chunks)} chunks...")
            notify("TTS Clipboard", f"Long text — processing {len(chunks)} chunks...")

            tmp_dir = tempfile.mkdtemp()
            chunk_files = []

            for i, chunk in enumerate(chunks):
                audio_content = synthesize_chunk(client, chunk, voice, audio_config)
                chunk_path = os.path.join(tmp_dir, f"chunk_{i:03d}.mp3")
                with open(chunk_path, "wb") as f:
                    f.write(audio_content)
                chunk_files.append(chunk_path)
                print(f"  Chunk {i + 1}/{len(chunks)} done")

            # Write ffmpeg concat list
            concat_list = os.path.join(tmp_dir, "concat.txt")
            with open(concat_list, "w") as f:
                for path in chunk_files:
                    f.write(f"file '{path}'\n")

            subprocess.run(
                [
                    "/opt/homebrew/bin/ffmpeg", "-y",
                    "-f", "concat", "-safe", "0",
                    "-i", concat_list,
                    "-c", "copy",
                    output_path,
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Clean up temp files
            for path in chunk_files:
                os.unlink(path)
            os.unlink(concat_list)
            os.rmdir(tmp_dir)

        print(f"Saved to {output_path}")
        subprocess.Popen(["open", "-a", "QuickTime Player", output_path])
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
