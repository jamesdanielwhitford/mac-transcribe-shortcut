# Sessions Overview

## Session log
| # | Date | Key outcomes |
|---|------|-------------|
| 001 | 2026-09-23 | Fixed intermittent QuickTime "file isn't compatible" error on long clipboard TTS by switching multi-chunk concat to raw PCM + single encode, and adding a verified QuickTime open with afplay fallback |

## Current status
- `tts-clipboard.py` fix applied and synced between the live running copy
  (`~/CODE/voice-transcribe/`) and this repo. LaunchAgent reloaded and
  running the fixed version.
- Fix appears to have resolved the reported failures in this session's
  testing, but the original bug was intermittent, so this is not a fully
  confirmed fix yet - watching for recurrence.

## Next session checklist
- [ ] Watch for recurrence of the QuickTime "file isn't compatible" error
      during normal use
- [ ] If it recurs, check for the afplay fallback notification (means the
      guard worked) vs. a raw QuickTime error (means the guard itself failed)
- [ ] Consider consolidating the three script locations
      (`~/CODE/voice-transcribe/`, `~/Documents/CODE/voice-transcribe/`,
      loose `~/voice-transcribe.py`) into one canonical source
