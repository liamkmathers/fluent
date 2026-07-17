# Frequency-First Curriculum

This directory adds **frequency-prioritized learning** to Fluent: teach the words
and grammar you'll use most, first. The most common ~2,000 Italian word-forms
cover ~80% of everyday speech and text — so learning in frequency order buys the
most real-world comprehension per unit of effort.

## Files

| File | What it is |
|------|-----------|
| `italian-frequency.json` | Ranked word list (rank = teaching order) with `cumulative_coverage` — the share of running text the top-N words account for. **Order + coverage only; meanings/examples are generated live by the tutor.** |
| `italian-grammar-syllabus.json` | 30 grammar rules ordered by everyday utility, each with prerequisites and the CEFR band it belongs to. |
| `next_items.py` | The selector the skills call. `select` returns the next unlearned highest-frequency words + live coverage; `mark` records introduced words. State lives in `<data_dir>/frequency-progress.json`. |
| `build_frequency.py` | Regenerates `italian-frequency.json` from a raw `word count` corpus. |
| `sources/it_full.txt` | Raw corpus: hermitdave/FrequencyWords (OpenSubtitles 2018, MIT). |

## Using the selector

```bash
# Next 12 content words to drill (function words skipped — those are grammar)
python3 next_items.py select --n 12 --content-only

# Next 10 items including function words (for coverage-style intro)
python3 next_items.py select --n 10

# Machine-readable, for a skill to consume
python3 next_items.py select --n 10 --content-only --json

# Record words after a session presented them
python3 next_items.py mark --words "cosa,bene,fare,grazie"
```

Coverage checkpoints for Italian (word-form based):

| Words known | Coverage of everyday Italian |
|-------------|------------------------------|
| 124 | 50% |
| ~1,870 | 80% |
| 6,000 | ~89% |

## How words are taught (not a flat list)

Frequency decides *priority*, but the tutor never presents words as disconnected
pairs. Two rules in the skills guarantee coherence:

- **Grammar backbone first.** The grammar syllabus front-loads the sentence-building
  machinery (essere/avere, articles, common verbs, prepositions) with prerequisites,
  so the learner can form real sentences within the first sessions.
- **i+1 comprehensible input.** Every new word is introduced inside a sentence whose
  other words the learner already knows. Coherence is structural, not accidental —
  you get *"La casa è grande,"* never *"door hospital."* Sentences get richer as
  known vocabulary grows.

The selector returns *which* words are eligible next; the tutor clusters each
session's batch into a coherent mini-lesson and uses every new word in a full
sentence.

## Design notes / honest caveats

- **Word-form, not lemma.** `sono`, `è`, `siamo` are counted separately, so
  coverage is spread across inflections. This is realistic for a learner reading
  in the wild, but a lemma-grouped list would hit 80% with fewer *dictionary*
  words. Lemmatization (via spaCy `it_core_news_sm`) is a future enhancement.
- **Coverage denominator is the full corpus** (247M tokens), including the tokens
  filtered out as junk — so "80% coverage" honestly means 80% of real running text.
- **Function words** (`il`, `di`, `che`, `non`, essere/avere forms, ...) dominate
  the top ranks. They're taught in context through the grammar syllabus, so
  `--content-only` skips them when offering flashcard vocab. They still count
  toward coverage once known.
- **Corpus is conversational** (film subtitles): great for speaking/listening
  vocabulary, lighter on formal/written registers.

## Regenerating or adding another language

```bash
# Download that language's list from hermitdave/FrequencyWords, then:
python3 build_frequency.py --source sources/es_full.txt \
    --out spanish-frequency.json --top 6000 --language Spanish
```

`next_items.py` works for any generated `*-frequency.json`; pass `--corpus`.
To port `--content-only`, extend `FUNCTION_WORDS` in `next_items.py` with that
language's grammatical words (or leave it — it only affects flashcard filtering).
Grammar syllabi are hand-authored per language.

## Credit

Frequency data: [hermitdave/FrequencyWords](https://github.com/hermitdave/FrequencyWords)
(OpenSubtitles 2018, MIT License). Built on top of [m98/fluent](https://github.com/m98/fluent).
