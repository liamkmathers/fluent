---
name: fluent-vocab
description: Run an interactive vocabulary drill session with flashcard-style prompts, spaced repetition, and per-answer feedback. Triggered only when the learner types /fluent-vocab. Reads spaced-repetition / mistakes / mastery DBs to pick words, presents one word at a time, scores each answer, and calls fluent-db-updater at the end.
allowed-tools: Read, Write, Bash
disable-model-invocation: true
---

# Vocabulary Drill Session

## Overview

Flashcard-style vocabulary practice using spaced repetition. One word at a time, immediate feedback, DB update at the end. Interleaves three modes (recognition, production, cloze) to force active recall rather than passive re-reading.

## When to Use

Trigger this skill only when the learner types `/fluent-vocab`. The skill is gated with `disable-model-invocation: true` — a false-positive auto-trigger would launch a 15-min interactive session and mutate 6 JSON databases. Not worth the risk.

Skip this skill if no vocabulary items are due and no new words are queued — offer `/fluent-review` or `/fluent-learn` instead.

## Instructions

### 1. Load vocabulary data

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-${CLAUDE_PROJECT_DIR:-.}}/.claude/hooks/read-db.py"
```

If the helper is unavailable, resolve `<data_dir>` via `fluent_paths.data_dir()` then read:

- `<data_dir>/spaced-repetition.json`
- `<data_dir>/mistakes-db.json`
- `<data_dir>/mastery-db.json`
- `<data_dir>/learner-profile.json` (for target_language, name, level)

If any are missing, direct the learner to `/fluent-setup` and stop.

### 2. Select words

Priority order:

1. Items in `spaced-repetition.review_queue.today` with `item_type == "vocabulary"`.
2. Words from `mistakes-db.json` where `category == "vocabulary"` and `mastery_level <= 2`.
3. **New words in frequency order** — pull from the frequency-first curriculum so
   the learner always learns the most useful unlearned words next. Do not guess
   which words are "common"; ask the selector:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT:-${CLAUDE_PROJECT_DIR:-.}}/curriculum/next_items.py" \
       select --n 10 --content-only --json
   ```

   It returns the next highest-frequency words the learner hasn't been introduced
   to yet, plus `known_coverage_pct` (how much of everyday Italian they already
   understand). Use these as the new words for the session. `--content-only` skips
   grammatical function words — those are taught by the grammar syllabus, not
   drilled as flashcards. If the curriculum is absent (non-Italian learner, or
   corpus not built), fall back to selecting sensible high-frequency words yourself.

Limit: `spaced-repetition.daily_limits.review_items_per_day` (default 20).

#### Contextual sequencing (do NOT present words as a disconnected list)

Frequency sets *priority*, but you assemble each session so words are learned in
context, never as random isolated pairs:

- **i+1 rule.** Introduce every new word inside an example sentence whose every
  *other* word the learner already knows (from `frequency-progress.json` known
  words + mastered grammar rules). The learner should be able to parse the whole
  sentence except the one new word. As known vocabulary grows, sentences get
  richer on their own.
- **Grammar-gated.** Only build sentences using grammar rules the learner has met.
  If they only know present-tense `essere` + articles + a few nouns, keep sentences
  at that structure ("La casa è grande") — don't jump to past tense.
- **Cluster the batch coherently.** From the frequency-ranked words the selector
  returns, group the session's new words into a small theme or a set that combines
  into sentences together (e.g. a verb + nouns it takes), rather than presenting
  them in raw rank order. Frequency decides *which* words are eligible; you decide
  the *within-session order* so the mini-lesson hangs together.
- **Always end able to say something.** Every new word should appear in at least one
  full sentence the learner produces or completes — never just "word = translation".

### 3. Present one word at a time

Rotate the three modes so the session is not monotonous.

**Recognition** (target_language → native):

```markdown
## Word {N}/{total}

**{target_language}:** {word}

**Context:** {example_sentence}

**What does it mean in {native_language}?**

**Type your answer:**
```

**Production** (native → target_language):

```markdown
## Word {N}/{total}

**{native_language}:** {word}

**Use it in a sentence (optional).**

**How do you say this in {target_language}?**

**Type your answer:**
```

**Cloze** (fill in the blank):

```markdown
## Word {N}/{total}

**Complete the sentence:**

{target_language sentence with _____ where the word goes}

**Type the missing word:**
```

### 4. Feedback after each answer

Use the `fluent-feedback-formatter` skill's template. Score out of 10, tag severity.

Track the answer for the end-of-session DB update:

- Add to `review_results[]` with `quality = floor(score / 2)` (see `fluent-sm2-calculator` skill).
- If the learner met a new word, stage it for `new_vocabulary[]`.
- If the learner made an error, stage it for `errors[]`.

Do **not** call `update-db.py` after every word — batch at session end.

### 5. Session summary

```markdown
## 📚 Vocabulary Session Complete!

**Words Reviewed:** {N}
**Accuracy:** {X}%
**New Words Learned:** {Y}
**Words Mastered (→ level 5):** {Z}

**Strong:** {list words with mastery 4-5}
**Need more practice:** {list words with mastery 0-2}

**Next review:**
- Tomorrow: {count} words
- This week: {count} words

{target-language "well done"}! 🌟
```

### 6. Update all databases

If this session introduced new words from the frequency curriculum, record them
so the next session continues from the right place:

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-${CLAUDE_PROJECT_DIR:-.}}/curriculum/next_items.py" \
    mark --words "cosa,bene,fare,grazie"
```

Then call the `fluent-db-updater` skill's workflow — one `update-db.py` invocation with:

- `session_id`, `date`, `duration_minutes`
- `command_used: "/fluent-vocab"`
- `skills_practiced: ["vocabulary"]`
- `skill_scores.vocabulary`: `{exercises, correct, time_minutes}`
- `errors[]`, `new_vocabulary[]`, `review_results[]` collected during the session
- `focus_next_session[]` — top 2-3 weak words

## Examples

### Example 1 — recognition drill

> ## Word 1/15
>
> **Dutch:** de keuken
>
> **Context:** "De keuken is klein maar mooi."
>
> **What does it mean in English?**
>
> Type your answer:

Learner: "the kitchen"

> ✅ Exactly.
>
> **Answer:** the kitchen
> **Meaning:** A room used for cooking and food preparation.
> **Example:** "De keuken is klein maar mooi." (The kitchen is small but pretty.)
>
> **Score: 10/10** 🎯
>
> ---

### Example 2 — production with error

> ## Word 7/15
>
> **English:** to write
>
> **How do you say this in Dutch?**

Learner: "schrijven"

> ✅ Correct — infinitive form.
>
> Now: can you also give the first-person present? (I write → …)

### Example 3 — session end summary

> ## 📚 Vocabulary Session Complete!
>
> **Words Reviewed:** 15
> **Accuracy:** 80% (12/15)
> **New Words Learned:** 3
> **Words Mastered:** 1
>
> **Need more practice:** de sleutel, het raam, gisteren
>
> **Next review:** Tomorrow 4 words, this week 8 words.
>
> Goed gedaan! 🌟

## Critical Rules

- **One word at a time.** Wait for the learner's answer before showing the next.
- **Immediate feedback** after each — use `fluent-feedback-formatter`.
- **Mix modes.** Don't drill 20 recognition prompts in a row — interleave for discrimination.
- **Use target language** for greetings + transitions when the learner is B1+; for A1-A2 mix target + native.
- **Never** update the DBs mid-session — batch at end.
- **Never auto-invoke.** This skill is gated; must fire only on explicit `/fluent-vocab`.
- **New words come from the frequency selector, in order.** Don't introduce a rarer word before a more common unlearned one — the whole point is maximum coverage per word. Always `mark` new words after presenting them.

## Tips for the Learner (append if they seem tired or unsure)

- Review daily for best retention — spaced repetition depends on it.
- Focus time on weak words (mastery 0-2), not already-strong ones.
- Use words in sentences to build contextual memory.
- Say words out loud even though you're typing.
