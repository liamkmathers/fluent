---
name: fluent-tips
description: Show the learner's personal cheat-sheet of Italian "tricks" — the little rules-of-thumb they've hit in sessions (in vs a for places, false friends, gender traps, piacere agreement). Use when the learner types /fluent-tips or asks "show my tricks / cheat sheet / what tips have I learned / that rule about X". Read-only — safe to auto-invoke.
allowed-tools: Read, Bash
---

# Tricks Cheat-Sheet

## Overview

The learner's growing personal reference of small, high-leverage rules — the
"little hacks" that don't fit neatly into the grammar syllabus but trip everyone
up (e.g. *in* for countries vs *a* for cities; *caldo* = hot not cold; *mi piace*
vs *mi piacciono*). Tricks accumulate automatically as the feedback formatter
captures them during practice; this skill displays them. Read-only.

## When to Use

- Learner types `/fluent-tips`.
- Learner asks "show my cheat sheet / my tricks / the tips I've learned", or
  "what was that rule about {topic}".
- End of a session, if the learner wants a quick reference of what to remember.

Safe to auto-invoke — it's a pure read.

## Instructions

### 1. Load the tricks

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-${CLAUDE_PROJECT_DIR:-.}}/curriculum/tricks.py" list
```

For a specific topic, filter:

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-${CLAUDE_PROJECT_DIR:-.}}/curriculum/tricks.py" list --category prepositions
```

### 2. First-run seeding

If the list is empty (learner never triggered a capture yet), offer to seed the
curated Italian starter set so the cheat-sheet isn't blank:

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-${CLAUDE_PROJECT_DIR:-.}}/curriculum/tricks.py" seed
```

Only seed on the learner's first visit or if they ask — don't re-seed every time.

### 3. Present the cheat-sheet

Render grouped by category, learner-friendly. Put the tricks they've reinforced
most (⭐, times_reinforced ≥ 3) at the top of each group — those are the ones
that keep catching them.

```markdown
# 🧠 {name}'s Italian Cheat-Sheet

*{N} tricks — the little rules you've picked up. ⭐ = keeps coming up.*

## Prepositions
- **in** for countries, **a** for cities ⭐
  - Vivo *in* Svizzera · Vivo *a* Zurigo
- **di** for where you're from — *Sono di Los Angeles*

## False Friends
- **caldo** = hot (not cold!) — *Ho caldo*
...
```

### 4. Optional: quiz me

If the learner asks to be tested, pick 3-4 tricks and turn them into quick
fill-in prompts, then update reinforcement via the feedback path as normal.

## Critical Rules

- **Read-only.** Never edit `tricks-db.json` here — capture happens in the
  feedback formatter, display happens here.
- **Group by category**, most-reinforced first.
- **Don't fabricate tricks.** Show only what's in the learner's store (plus the
  curated seed if they opted in).
- **Cite the learner by name** from `learner-profile.json`.

## How Tricks Get Captured

The `fluent-feedback-formatter` skill appends a trick whenever a correction
carries a generalizable rule (not a one-off typo). Over weeks this becomes a
personalized cheat-sheet of exactly the things *this* learner keeps needing —
far more useful than a generic tips page.
