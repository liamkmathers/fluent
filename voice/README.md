# Voice Layer

Adds **spoken input and output** to Fluent: the tutor speaks Italian aloud (TTS),
the learner replies out loud, and the reply is transcribed (STT) and optionally
scored for pronunciation. Used by the `fluent-speaking-voice` skill.

Because the Claude Code CLI is text-only, audio is handled by these standalone
scripts that the skill shells out to. Recording auto-stops on silence, so a
session flows without interactive key-presses.

## Scripts

| Script | Does | Default backend |
|--------|------|-----------------|
| `tts.py` | Speak text aloud | macOS `say` (offline, free, Italian voices) |
| `stt.py` | Record mic (silence auto-stop) + transcribe | `faster-whisper` (local) |
| `pronounce.py` | Score pronunciation vs a reference sentence | Azure if keys present, else transcript-match heuristic |

Each supports `--check` to verify it's usable without running a full session.

## Quick start

```bash
# 1. TTS works out of the box on macOS — no install:
python3 voice/tts.py "Buongiorno! Come stai?"

# 2. For recording + transcription, install the local stack:
pip install -r voice/requirements.txt          # sounddevice, numpy, faster-whisper
#    (if sounddevice fails to build:  brew install portaudio  then retry)

# 3. Verify:
python3 voice/stt.py --check
python3 voice/pronounce.py --check

# 4. Try a round trip:
python3 voice/tts.py "Ripeti dopo di me: vorrei un caffè"
python3 voice/pronounce.py --reference "vorrei un caffè" --record
```

## Backends (all pluggable via env vars)

| Env var | Options | Notes |
|---------|---------|-------|
| `FLUENT_TTS_BACKEND` | `say` (default), `openai`, `elevenlabs`, `azure` | cloud = more natural voices |
| `FLUENT_TTS_VOICE` | e.g. `Alice`, `Eddy`, `Flo` | macOS Italian voices |
| `FLUENT_STT_BACKEND` | `faster-whisper` (default), `openai`, `azure` | |
| `FLUENT_WHISPER_MODEL` | `base` (default), `small`, `medium` | bigger = more accurate, slower |
| `AZURE_SPEECH_KEY` / `AZURE_SPEECH_REGION` | — | unlocks phoneme-level pronunciation scoring |
| `OPENAI_API_KEY` | — | for OpenAI TTS/Whisper backends |
| `ELEVENLABS_API_KEY` | — | for ElevenLabs TTS |

## Pronunciation scoring tiers

- **azure** — per-word and per-phoneme accuracy + fluency/completeness/prosody.
  Billed as part of Speech-to-Text (no extra charge); free tier ~5 audio-hours/month,
  which covers a lot of daily practice. Best experience.
- **heuristic** (no Azure) — transcribes the audio with local Whisper and compares
  to the reference sentence at the word level. Catches wrong/missing words, not
  phoneme accuracy. Fully offline.

## Cost note

Everything runs **free and offline** by default (macOS `say` + local Whisper).
You only pay if you opt into a cloud backend. Azure pronunciation assessment is
the one most worth the (small, often-free-tier) cost for a language app, since
phoneme-level feedback is the real pronunciation unlock.
