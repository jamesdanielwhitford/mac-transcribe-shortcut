#!/bin/bash
set -e

# TTS Clipboard setup script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_PATH="$SCRIPT_DIR/tts-clipboard.py"
PLIST_PATH="$HOME/Library/LaunchAgents/com.tts-clipboard.plist"
LOG_PATH="$HOME/tts-clipboard.log"

echo "TTS Clipboard Setup"
echo "==================="

# Check for Homebrew
if ! command -v brew &>/dev/null; then
    echo "Error: Homebrew is not installed. Install it from https://brew.sh then re-run this script."
    exit 1
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install pynput google-cloud-texttospeech

# Get Google credentials path
echo ""
echo "You need a Google Cloud service account JSON key with the Text-to-Speech API enabled."
echo "See: https://cloud.google.com/text-to-speech/docs/before-you-begin"
echo ""
read -rp "Enter the full path to your Google service account JSON file: " CREDENTIALS_PATH

if [ ! -f "$CREDENTIALS_PATH" ]; then
    echo "Error: File not found at '$CREDENTIALS_PATH'."
    exit 1
fi

# Create plist from template
sed \
    -e "s|SCRIPT_PATH|$SCRIPT_PATH|g" \
    -e "s|GOOGLE_CREDENTIALS_PATH|$CREDENTIALS_PATH|g" \
    -e "s|LOG_PATH|$LOG_PATH|g" \
    "$SCRIPT_DIR/com.tts-clipboard.plist.template" > "$PLIST_PATH"

echo "Created launch agent at $PLIST_PATH"

# Load the agent
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

echo ""
echo "Done! TTS Clipboard is running."
echo ""
echo "IMPORTANT: You must grant Accessibility permission before the shortcut will work."
echo "  Open System Settings > Privacy & Security > Accessibility"
echo "  and enable access for Terminal."
echo ""
echo "Then run this in a terminal once to activate permissions:"
echo "  python3 $SCRIPT_PATH"
echo ""
echo "Copy some text, press Ctrl+Option+V to test. Close the terminal when confirmed."
echo "The shortcut will continue working in the background."
echo ""
echo "Audio files are saved to ~/Desktop/TTS Recordings/ as tts_YYYY-MM-DD_HH-MM-SS.mp3"
