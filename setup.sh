#!/bin/bash
set -e

# Voice Transcribe setup script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_PATH="$SCRIPT_DIR/voice-transcribe.py"
PLIST_PATH="$HOME/Library/LaunchAgents/com.voice-transcribe.plist"
LOG_PATH="$HOME/voice-transcribe.log"

echo "Voice Transcribe Setup"
echo "======================"

# Check for Homebrew
if ! command -v brew &>/dev/null; then
    echo "Error: Homebrew is not installed. Install it from https://brew.sh then re-run this script."
    exit 1
fi

# Install sox
if ! command -v sox &>/dev/null; then
    echo "Installing sox..."
    brew install sox
else
    echo "sox already installed."
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install pynput requests

# Get API key
echo ""
read -rp "Enter your Mistral API key: " API_KEY
if [ -z "$API_KEY" ]; then
    echo "Error: API key cannot be empty."
    exit 1
fi

# Get sox path (Apple Silicon vs Intel)
SOX_PATH="$(which sox)"

# Update sox path in script
sed -i '' "s|/opt/homebrew/bin/sox|$SOX_PATH|g" "$SCRIPT_PATH"

# Create plist from template
sed \
    -e "s|SCRIPT_PATH|$SCRIPT_PATH|g" \
    -e "s|YOUR_API_KEY_HERE|$API_KEY|g" \
    -e "s|LOG_PATH|$LOG_PATH|g" \
    "$SCRIPT_DIR/com.voice-transcribe.plist.template" > "$PLIST_PATH"

echo "Created launch agent at $PLIST_PATH"

# Load the agent
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

echo ""
echo "Done! Voice Transcribe is running."
echo ""
echo "IMPORTANT: You must grant permissions before the shortcut will work."
echo "  1. Open System Settings > Privacy & Security > Accessibility"
echo "     and enable access for Terminal (or whichever app ran this script)."
echo "  2. Open System Settings > Privacy & Security > Microphone"
echo "     and enable access for Terminal."
echo ""
echo "Then run this in a terminal to activate permissions:"
echo "  python3 $SCRIPT_PATH"
echo ""
echo "Press Ctrl+Option+V once to confirm it works, then close the terminal."
echo "The shortcut will continue working in the background."
