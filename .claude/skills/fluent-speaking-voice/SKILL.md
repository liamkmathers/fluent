---
name: fluent-speaking-voice
description: Run a spoken conversation session — the tutor speaks Italian aloud (text-to-speech), the learner replies out loud, and the reply is transcribed and scored for both content and pronunciation. Triggered only when the learner types /fluent-speaking-voice. Uses the scripts in voice/ for audio. Falls back to typed input if the audio stack isn't installed.
allowed-tools: Read, Write, Bash
disable-model-invocation: true
---

# Speaking Practice (Voice)

## Overview

The spoken counterpart to `/fluent-speaking`. The tutor **speaks** each prompt in
Italian, the learner **answers out loud**, and their speech is transcribed and
scored for content *and* pronunciation. Like the typed version, prioritize
**communication first** — but here pronunciation is a real, tracked dimension.

Audio is handled by the standalone scripts in `voice/` (the CLI itself is
text-only). Recording auto-stops on silence, so turns flow without key-presses.

## When to Use

Trigger only when the learner types `/fluent-speaking-voice`. Gated with
`disable-model-invocation: true` — long interactive session, DB writes, and it
drives the microphone.

Skip below A1 mastery 2 — route to `/fluent-vocab` first to build a word bank.

## Instructions

### 0. Preflight the audio stack

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-${CLAUDE_PROJECT_DIR:-.}}/voice/tts.py" --check
python3 "${CLAUDE_PLUGIN_ROOT:-${CLAUDE_PROJECT_DIR:-.}}/voice/stt.py" --check
python3 "${CLAUDE_PLUGIN_ROOT:-${CLAUDE_PROJECT_DIR:-.}}/voice/pronounce.py" --check
```

- If **TTS** isn't ready → tell the learner and continue text-only (this becomes
  `/fluent-speaking`).
- If **STT** isn't ready → tell them how to enable it
  (`pip install -r voice/requirements.txt`) and offer to fall back to typed answers
  for this session.
- Report which **pronunciation tier** is active (azure = phoneme-level,
  heuristic = word-match). Never block the session on Azure being absent.

### 1. Load context

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-${CLAUDE_PROJECT_DIR:-.}}/.claude/hooks/read-db.py"
```

Need `learner-profile` (level, target language, name) and
`mastery-db.skills_mastery.speaking`.

### 2. Opening (speak it, too)

Show the intro text, then speak the greeting:

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-${CLAUDE_PROJECT_DIR:-.}}/voice/tts.py" "Ciao {name}! Oggi parliamo in italiano. Rispondi ad alta voce."
```

```markdown
# 🎙️ Italian Speaking Practice (Voice)

Ciao {name}! I'll **speak** each question — answer **out loud** and I'll listen.

**Pronunciation scoring:** {azure phoneme-level | word-match heuristic}
**Level:** {CEFR} · **Duration:** 15-20 min

When you see 🎤, speak your answer. I'll transcribe it and give feedback.
```

### 3. One question at a time — the voice turn

For each question:

1. **Speak the prompt** (and show the text):
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT:-${CLAUDE_PROJECT_DIR:-.}}/voice/tts.py" "{question in Italian}"
   ```
   ```markdown
   ## Question {N}: {topic}
   🔊 "{question in Italian}"  ({native-language gloss})

   🎤 **Speak your answer now...**
   ```

2. **Record + transcribe** (auto-stops on silence):
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT:-${CLAUDE_PROJECT_DIR:-.}}/voice/stt.py" --record --lang it
   ```
   Parse the JSON `transcript`. If empty/error, tell the learner "I didn't catch
   that — try again or type it," and retry once.

3. **Score pronunciation** against what you expected them to say. Use the learner's
   own transcript as the reference when the task is free-form, or the target phrase
   for a repeat-after-me drill:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT:-${CLAUDE_PROJECT_DIR:-.}}/voice/pronounce.py" --reference "{reference sentence}" --file "{audio_path from stt output}"
   ```

Reuse the `audio_path` from the STT result for `pronounce.py` — don't record twice.

### 4. Topics

Same ladder as `/fluent-speaking`: A2 → intros, daily routine, ordering food,
directions, shopping; B1+ → opinions, comparisons, narratives. Also offer a
**repeat-after-me** pronunciation drill: speak a target sentence, ask the learner
to say it back, and score it against that exact reference.

### 5. Feedback — content AND pronunciation

```markdown
{✅ or 🟡} {one-line encouragement}

**I heard:** "{transcript}"

**Communication:** {Clear / Mostly clear / Unclear}

**Pronunciation:** {pronunciation score}/100  ({tier})
- 🔴 Work on: {words with low accuracy / flagged phonemes, e.g. "gli" in famiglia}
- 🟢 Nailed: {high-accuracy words}

**Grammar notes:** (secondary)
- {only communication-blocking errors}

**Say it like a native:** "{natural phrasing}"  🔊
{optionally speak the model answer via tts.py so they hear the target}

**Score: {X}/10**  (Communication {Y}/5 · Pronunciation {P}/3 · Grammar {Z}/2)
```

When Azure tier is active, name specific mispronounced phonemes (it returns
per-word `error_type` and accuracy). On the heuristic tier, only flag words that
were wrong or missing — don't claim phoneme-level detail you don't have.

### 6. Session summary

```markdown
## 🎉 Voice Session Complete!

**Duration:** {X} min · **Questions:** {N}
**Avg pronunciation:** {P}/100
**Clear messages:** {count}/{N}

**Sounds to practice:** {recurring low-accuracy phonemes/words}
**Great pronunciation on:** {words}

**{target-language well done}!** 🌟
```

### 7. Update databases

Use the `fluent-db-updater` skill as usual:

- `command_used: "/fluent-speaking-voice"`, `skills_practiced: ["speaking"]`
- `skill_scores.speaking: {exercises: N, correct: clear_answers, time_minutes}`
- `errors[]` — communication-blocking only.

Additionally, append this session's pronunciation results to
`<data_dir>/pronunciation-db.json` (schema in
`data-examples/pronunciation-db-template.json`): per-utterance scores, and
increment `problem_sounds` for recurring low-accuracy phonemes/words so future
sessions can target them.

Save the exchange to `/results/fluent-speaking-voice-session-{NNN}.md`.

## Critical Rules

- **Never block on cloud services.** macOS `say` + local Whisper must be enough to
  run. Azure only upgrades pronunciation detail.
- **Reuse the recorded audio** for scoring — record once per turn.
- **Communication first**, pronunciation second, grammar third. Don't let a good
  message with a rolled-r miss score like a failure.
- **Speak model answers** so the learner hears the target, not just reads it.
- **Graceful fallback to typed input** whenever STT fails or the learner asks.
- **Never auto-invoke.** Gated; explicit `/fluent-speaking-voice` only.
- **Don't over-correct.** One or two priority sounds per turn, not every phoneme.

## Language Reference — Italian sounds that trip learners

- **gli** — palatal, like "lli" in million (famiglia, figli)
- **gn** — like "ny" in canyon (bagno, signore)
- **c/g before e/i** — soft (ciao, gelato) vs hard before a/o/u (casa, gatto)
- **r** — tapped/trilled, not the English r
- **double consonants** — genuinely held longer (nonno vs nono, sette vs sete)
- **stress** — often penultimate, but città, perché stress the final vowel
