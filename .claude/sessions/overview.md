# Sessions Overview

## Session log
| # | Date | Key outcomes |
|---|------|-------------|
| 001 | 2026-09-23 | Fixed intermittent QuickTime "file isn't compatible" error via raw-PCM concat + verified open; added URL-to-speech (fetch article, speak text instead of raw URL); removed the uncontrollable afplay fallback after it fired unexpectedly; fixed a Playwright browser version mismatch blocking JS-page extraction |

## Current status
- `tts-clipboard.py` and new `extract_url_text.py` synced between the live
  running copy (`~/CODE/voice-transcribe/`) and this repo. LaunchAgent
  reloaded and running the current version.
- QuickTime playback: no more `afplay` fallback. If QuickTime can't be
  confirmed to have opened a file, the tool notifies and stops - the MP3
  stays on Desktop either way. Nothing plays without QuickTime's controls.
- URL-to-speech: copying a bare URL (and only a URL) to the clipboard now
  fetches and speaks the article instead of reading the URL aloud. Falls
  back to speaking the literal URL on any extraction failure. Verified
  end-to-end against a real article. Depends on
  `~/.claude/skills/better-research` staying present.
- Playwright's browser binary for this feature's `uv`-resolved environment
  is now correctly installed (chromium 1243) - JS-rendered pages extract
  correctly instead of silently falling back to the raw URL.

## Next session checklist
- [ ] Watch for recurrence of the QuickTime "file isn't compatible" open
      failure during normal use - it now shows as a stop-and-notify instead
      of silent afplay playback, but the underlying flakiness isn't fully
      root-caused, only worked around
- [ ] Consider consolidating the three script locations
      (`~/CODE/voice-transcribe/`, `~/Documents/CODE/voice-transcribe/`,
      loose `~/voice-transcribe.py`) into one canonical source
- [ ] Try the URL-to-speech feature on a few more real links during normal
      use to build confidence beyond the one verified end-to-end run
