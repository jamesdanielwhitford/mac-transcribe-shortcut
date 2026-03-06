# Voice Transcribe

A macOS global keyboard shortcut that records your voice, transcribes it using Mistral's Voxtral model, and copies the result to your clipboard.

**Ctrl+Option+V** to start recording. Press again to stop and transcribe.

## Requirements

- macOS (Apple Silicon or Intel)
- Python 3
- A [Mistral API key](https://console.mistral.ai/)
- [Homebrew](https://brew.sh)

## Setup

```bash
git clone https://github.com/yourusername/voice-transcribe.git
cd voice-transcribe
chmod +x setup.sh
./setup.sh
```

The setup script will:
1. Install `sox` via Homebrew
2. Install Python dependencies (`pynput`, `requests`)
3. Ask for your Mistral API key
4. Create and load a login agent so it auto-starts at login

## Granting permissions

macOS requires explicit permission for global keyboard monitoring and microphone access. After running setup:

1. Open **System Settings > Privacy & Security > Accessibility** and enable Terminal
2. Open **System Settings > Privacy & Security > Microphone** and enable Terminal

Then run this once in a terminal to let macOS prompt you:

```bash
python3 voice-transcribe.py
```

Press **Ctrl+Option+V** to confirm it works, then close the terminal. The background agent will take over.

## Managing the background process

```bash
# Stop
launchctl unload ~/Library/LaunchAgents/com.voice-transcribe.plist

# Start
launchctl load ~/Library/LaunchAgents/com.voice-transcribe.plist

# View logs
tail -f ~/voice-transcribe.log
```

## How it works

- **pynput** listens globally for Ctrl+Option+V
- **sox** records audio from your default microphone at 16kHz
- The audio is sent to Mistral's `/v1/audio/transcriptions` endpoint using the `voxtral-mini-latest` model
- The transcribed text is copied to your clipboard via `pbcopy`
- macOS notifications confirm each step
