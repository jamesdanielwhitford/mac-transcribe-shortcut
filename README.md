# Voice Transcribe

Two macOS global keyboard shortcuts for voice and text:

- **Ctrl+Option+C** — record your voice, transcribe it, copy to clipboard (speech to text)
- **Ctrl+Option+V** — read your clipboard text aloud and save as MP3 (text to speech)

Both run silently in the background and start automatically at login.

---

## Tool 1: Voice Transcribe (Ctrl+Option+C)

Records your microphone and transcribes speech to text using Mistral's Voxtral model. The result is copied to your clipboard.

### Requirements

- macOS (Apple Silicon or Intel)
- Python 3
- A [Mistral API key](https://console.mistral.ai/)
- [Homebrew](https://brew.sh)

### Setup

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

### Granting permissions

After running setup:

1. Open **System Settings > Privacy & Security > Accessibility** and enable Terminal
2. Open **System Settings > Privacy & Security > Microphone** and enable Terminal

Then run this once in a terminal to let macOS prompt you:

```bash
python3 voice-transcribe.py
```

Press **Ctrl+Option+C** to confirm it works, then close the terminal. The background agent takes over.

### Managing the agent

```bash
# Stop
launchctl unload ~/Library/LaunchAgents/com.voice-transcribe.plist

# Start
launchctl load ~/Library/LaunchAgents/com.voice-transcribe.plist

# View logs
tail -f ~/voice-transcribe.log
```

### How it works

- **pynput** listens globally for Ctrl+Option+C
- **sox** records audio from your default microphone at 16kHz
- Audio is sent to Mistral's `/v1/audio/transcriptions` endpoint using `voxtral-mini-latest`
- Transcribed text is copied to your clipboard via `pbcopy`
- macOS notifications confirm each step

---

## Tool 2: TTS Clipboard Reader (Ctrl+Option+V)

Reads whatever text is in your clipboard aloud using Google Cloud TTS (WaveNet). The audio is played immediately and saved as an MP3 to `~/Desktop/TTS Recordings/` for future playback.

### Requirements

- macOS
- Python 3
- A Google Cloud account with the Text-to-Speech API enabled

### Google Cloud setup

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (e.g. "voice-tts")
3. Search for **Text-to-Speech API** and click **Enable**
4. Go to **IAM & Admin > Service Accounts**
5. Click **+ Create Service Account**, give it a name, click **Create and Continue**
6. Assign the role **Basic > Editor** (or **Cloud Text-to-Speech > Cloud Text-to-Speech Client**), click **Done**
7. Click the service account, go to the **Keys** tab
8. Click **Add Key > Create new key**, choose **JSON**, click **Create**
9. Move the downloaded JSON to a safe location outside any repo:

```bash
mkdir -p ~/.config/gcloud
mv ~/Downloads/your-key-file.json ~/.config/gcloud/tts-service-account.json
```

### Free tier and pricing

| Voice type | Free tier | Paid rate |
|------------|-----------|-----------|
| WaveNet | 4 million chars/month | $4 per 1M chars |
| Neural2 | 1 million chars/month | $16 per 1M chars |

WaveNet has a 4x larger free tier and is 4x cheaper. A typical clipboard read is a few hundred characters, so you would need thousands of uses per month to incur any cost.

To protect against unexpected charges, set a budget in **Billing > Budgets & alerts** (e.g. $1/month) and cap daily usage in **APIs & Services > Text-to-Speech API > Quotas** (e.g. 10,000 characters/day).

### Setup

```bash
chmod +x setup-tts.sh
./setup-tts.sh
```

When prompted, enter the full path to your service account JSON file (e.g. `/Users/yourname/.config/gcloud/tts-service-account.json`).

The script will install Python dependencies and load the background agent.

### Granting permissions

1. Open **System Settings > Privacy & Security > Accessibility** and enable Terminal

Then run this once to trigger the permission prompt:

```bash
GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcloud/tts-service-account.json python3 tts-clipboard.py
```

Copy some text, press **Ctrl+Option+V** to confirm it works, then close the terminal.

### Changing the voice

Edit `VOICE_NAME` in `tts-clipboard.py`. Default is `en-US-Wavenet-F` (female). Other options:

| Voice | Type | Gender |
|-------|------|--------|
| `en-US-Wavenet-F` | WaveNet | Female |
| `en-US-Wavenet-G` | WaveNet | Female |
| `en-US-Wavenet-H` | WaveNet | Female |
| `en-US-Wavenet-D` | WaveNet | Male |
| `en-US-Neural2-F` | Neural2 | Female |
| `en-US-Neural2-C` | Neural2 | Male |

### Managing the agent

```bash
# Stop
launchctl unload ~/Library/LaunchAgents/com.tts-clipboard.plist

# Start
launchctl load ~/Library/LaunchAgents/com.tts-clipboard.plist

# View logs
tail -f ~/tts-clipboard.log
```

---

## Verify both are running

```bash
launchctl list | grep -E "voice-transcribe|tts-clipboard"
```

Both process IDs should appear.
