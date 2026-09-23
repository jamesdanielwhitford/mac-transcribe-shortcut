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
import re
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

EXTRACT_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extract_url_text.py")
UV_BIN = "/opt/homebrew/bin/uv"
EXTRACT_TIMEOUT_SECS = 45  # requests-only fetches finish in ~1-3s; Playwright
                           # fallback (JS-rendered pages) can take 10-25s per
                           # research_lib's own PLAYWRIGHT_NAV_TIMEOUT (25s) plus
                           # settle/poll waits — 45s gives real Playwright runs
                           # headroom without hanging the hotkey indefinitely.

tts_lock = threading.Lock()
pressed_keys = set()


def notify(title, message):
    def esc(s):
        return s.replace("\\", "\\\\").replace('"', '\\"')
    subprocess.run([
        "osascript", "-e",
        f'display notification "{esc(message)}" with title "{esc(title)}"'
    ])


def get_clipboard():
    result = subprocess.run("pbpaste", capture_output=True)
    return result.stdout.decode("utf-8", errors="replace").strip()


_URL_ONLY_RE = re.compile(
    r'^(?:https?://|www\.)\S+$',
    re.IGNORECASE,
)


def is_url_only(text):
    """True if the entire (already-stripped) clipboard string is one URL and
    nothing else — no surrounding prose, no trailing sentence. Requires a
    scheme (http/https) or a leading 'www.' so we don't false-positive on
    ordinary text that merely contains a bare domain-looking token (e.g.
    'check out foo.com' or a sentence ending in an abbreviation like 'etc.')."""
    if " " in text or "\n" in text or "\t" in text:
        return False
    return bool(_URL_ONLY_RE.match(text))


def extract_article_text(url):
    """Run extract_url_text.py via `uv run` and return (title, text).
    Raises RuntimeError with a human-readable message on any failure
    (non-zero exit, timeout, unparsable output)."""
    try:
        result = subprocess.run(
            [UV_BIN, "run", EXTRACT_SCRIPT, url],
            capture_output=True, text=True,
            timeout=EXTRACT_TIMEOUT_SECS,
            cwd=os.path.dirname(EXTRACT_SCRIPT),
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"timed out fetching article after {EXTRACT_TIMEOUT_SECS}s")

    if result.returncode != 0:
        err = (result.stderr or "").strip().splitlines()
        detail = err[-1] if err else f"exit code {result.returncode}"
        raise RuntimeError(f"couldn't extract article: {detail}")

    stdout = result.stdout
    if "\n\n" not in stdout:
        raise RuntimeError("unexpected output from extractor")
    title, text = stdout.split("\n\n", 1)
    title = title.strip()
    text = text.strip()
    if not text:
        raise RuntimeError("extractor returned no article text")
    return title, text


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


# LINEAR16 (raw PCM in a WAV wrapper) used for multi-chunk requests only.
# Concatenating independently-generated MP3s via ffmpeg (either the concat
# demuxer or the concat filter) produces files QuickTime Player sometimes
# rejects with "file isn't compatible" even though the audio decodes fine
# elsewhere. Raw PCM chunks can be concatenated at the sample level with no
# container ambiguity, then encoded to MP3 exactly once at the end.
PCM_SAMPLE_RATE = 24000
PCM_AUDIO_CONFIG = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.LINEAR16,
    sample_rate_hertz=PCM_SAMPLE_RATE,
)


def synthesize_chunk_pcm(client, text, voice):
    synthesis_input = texttospeech.SynthesisInput(text=text)
    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=PCM_AUDIO_CONFIG,
    )
    # Strip the 44-byte WAV header, keep raw PCM samples for concatenation.
    return response.audio_content[44:]


def get_quicktime_doc_count():
    result = subprocess.run(
        ["osascript", "-e", 'tell application "QuickTime Player" to count documents'],
        capture_output=True, text=True,
    )
    try:
        return int(result.stdout.strip())
    except ValueError:
        return -1


def play_audio(path):
    """
    Open path in QuickTime Player. `open -a` only confirms Launch Services
    handed off the request — it returns success even when QuickTime itself
    later rejects the file, which is the failure mode this guards against.
    AppleScript's "open" command runs synchronously against the app itself,
    so we can verify success by checking the document count actually
    increased.

    Deliberately no afplay (or any other headless-player) fallback here: it
    plays audio with no window and no pause/stop control, and an earlier
    version of this function fell back to it silently — the user could end
    up with audio playing on their laptop they had no way to stop short of
    finding and killing the process. If QuickTime can't be confirmed to
    have opened the file, stop and say so; the MP3 is already saved to
    Desktop and can be opened manually.
    """
    before = get_quicktime_doc_count()
    posix_path = path.replace('"', '\\"')
    script = f'tell application "QuickTime Player" to open POSIX file "{posix_path}"'
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    after = get_quicktime_doc_count()

    if result.returncode == 0 and after > before:
        return

    notify("TTS Clipboard", "QuickTime couldn't open the file — it's saved on your Desktop")
    print(f"QuickTime failed to open {path}, not falling back to afplay")


def speak_clipboard():
    text = get_clipboard()
    if not text:
        notify("TTS Clipboard", "Clipboard is empty.")
        print("Clipboard is empty.")
        return

    if is_url_only(text):
        notify("TTS Clipboard", "Fetching article...")
        print(f"Fetching article: {text}")
        try:
            title, article_text = extract_article_text(text)
            text = f"{title}. {article_text}"
            print(f"Extracted \"{title}\" ({len(article_text)} chars)")
        except Exception as e:
            notify("TTS Clipboard", f"Couldn't fetch article ({e}) — speaking URL instead")
            print(f"Article extraction failed: {e}")
            # text stays as the original URL string; fall through to speak it literally

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
                f.flush()
                os.fsync(f.fileno())
        else:
            print(f"Text is long, splitting into {len(chunks)} chunks...")
            notify("TTS Clipboard", f"Long text — processing {len(chunks)} chunks...")

            tmp_dir = tempfile.mkdtemp()

            pcm_parts = []
            for i, chunk in enumerate(chunks):
                pcm_parts.append(synthesize_chunk_pcm(client, chunk, voice))
                print(f"  Chunk {i + 1}/{len(chunks)} done")

            combined_pcm_path = os.path.join(tmp_dir, "combined.pcm")
            with open(combined_pcm_path, "wb") as f:
                for part in pcm_parts:
                    f.write(part)

            # Single clean encode from raw PCM to MP3 — no container
            # splicing, so ffmpeg writes accurate duration/Xing headers.
            result = subprocess.run(
                [
                    "/opt/homebrew/bin/ffmpeg", "-y",
                    "-f", "s16le", "-ar", str(PCM_SAMPLE_RATE), "-ac", "1",
                    "-i", combined_pcm_path,
                    "-c:a", "libmp3lame", "-q:a", "2",
                    output_path,
                ],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr[-500:] if result.stderr else "ffmpeg failed")

            os.unlink(combined_pcm_path)
            os.rmdir(tmp_dir)

        file_size = os.path.getsize(output_path) if os.path.exists(output_path) else -1
        if file_size <= 0:
            raise RuntimeError(f"output file missing or empty before playback (size={file_size})")

        print(f"Saved to {output_path}")
        play_audio(output_path)
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
