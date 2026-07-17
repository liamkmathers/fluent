#!/usr/bin/env python3
"""
Build a frequency-ranked Italian vocabulary curriculum from a raw
`word count` frequency list (hermitdave/FrequencyWords, OpenSubtitles 2018).

Output: italian-frequency.json
  - ranked list of the most common words (order = teaching order)
  - cumulative_coverage: fraction of all running text these words account for
    (the "80/20" signal — the tutor teaches highest-coverage words first)

The corpus supplies ORDER + COVERAGE only. Meanings, example sentences and
cloze prompts are generated live by the tutor (Claude already knows Italian),
which keeps this file small and makes the same pipeline reusable for any
language: just point --source at that language's frequency list.

Usage:
  python3 build_frequency.py --source sources/it_full.txt --out italian-frequency.json --top 3000
"""
import argparse
import json
import re
import sys

# Italian lowercase letters incl. accented vowels; allow a trailing apostrophe
# for legitimate elided forms (l', un', dell', c', ...).
TOKEN_RE = re.compile(r"^[a-zàèéìíîòóùú]+['’]?$")

# Obvious non-Italian / subtitle-artifact tokens that survive the regex.
STOPWORD_JUNK = {"www", "http", "https", "com", "html", "ok", "okay"}


def load_counts(path):
    pairs = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            parts = line.split()
            if len(parts) != 2:
                continue
            word, count = parts
            try:
                count = int(count)
            except ValueError:
                continue
            pairs.append((word, count))
    return pairs


def is_clean(word):
    if word in STOPWORD_JUNK:
        return False
    if not TOKEN_RE.match(word):
        return False
    return True


def build(pairs, top):
    # Denominator = every token in the corpus, including ones we filter out,
    # so coverage honestly means "share of real running text".
    total_tokens = sum(c for _, c in pairs)

    entries = []
    running = 0
    rank = 0
    for word, count in pairs:  # already sorted desc in source
        if not is_clean(word):
            continue
        rank += 1
        running += count
        entries.append({
            "rank": rank,
            "word": word,
            "count": count,
            "cumulative_coverage": round(running / total_tokens, 5),
        })
        if rank >= top:
            break

    # Coverage checkpoints: how many words to reach each comprehension band.
    checkpoints = {}
    for band in (0.50, 0.80, 0.90, 0.95):
        hit = next((e["rank"] for e in entries if e["cumulative_coverage"] >= band), None)
        checkpoints[f"{int(band*100)}%"] = hit

    return entries, total_tokens, checkpoints


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="sources/it_full.txt")
    ap.add_argument("--out", default="italian-frequency.json")
    ap.add_argument("--top", type=int, default=3000)
    ap.add_argument("--language", default="Italian")
    args = ap.parse_args()

    pairs = load_counts(args.source)
    if not pairs:
        sys.exit(f"No usable rows in {args.source}")

    entries, total_tokens, checkpoints = build(pairs, args.top)

    doc = {
        "metadata": {
            "language": args.language,
            "source": "hermitdave/FrequencyWords (OpenSubtitles 2018)",
            "source_license": "MIT",
            "method": "word-form frequency; cumulative_coverage over full corpus tokens",
            "total_corpus_tokens": total_tokens,
            "words_included": len(entries),
            "coverage_checkpoints_word_count": checkpoints,
            "note": "Teaching order = rank. Glosses/examples generated live by the tutor.",
        },
        "words": entries,
    }

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)

    print(f"Wrote {len(entries)} words -> {args.out}")
    print(f"Corpus tokens: {total_tokens:,}")
    print("Words needed for coverage band:")
    for band, n in checkpoints.items():
        print(f"  {band}: {n} words")


if __name__ == "__main__":
    main()
