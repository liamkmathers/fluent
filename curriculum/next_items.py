#!/usr/bin/env python3
"""
Frequency-first word selector for the Fluent tutor.

Single source of truth for "what should the learner study next" when the goal
is to cover the most everyday Italian per word learned.

Two sub-commands the skills call:

  select   Return the next N highest-frequency words the learner has NOT yet
           been introduced to, plus coverage stats. Read-only.

  mark     Record words as introduced (after a vocab/learn session presents
           them), so the next `select` continues from there. Writes
           <data_dir>/frequency-progress.json.

The learner's introduced-word state lives in <data_dir>/frequency-progress.json
— owned by this feature, decoupled from Fluent's 6 core DBs. Coverage numbers
come straight from the corpus's cumulative_coverage field.

Examples:
  python3 next_items.py select --n 10
  python3 next_items.py select --n 10 --json
  python3 next_items.py mark --words "parlare,casa,acqua,bene"
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CORPUS = os.path.join(HERE, "italian-frequency.json")
PROGRESS_FILENAME = "frequency-progress.json"

# High-frequency Italian grammatical/function words. These dominate the top of
# any frequency list but are taught in context via the grammar syllabus, not as
# vocab flashcards. `select --content-only` skips them when offering NEW words to
# drill; they still count toward coverage once the learner knows them.
FUNCTION_WORDS = {
    # articles
    "il", "lo", "la", "l'", "i", "gli", "le", "un", "uno", "una", "un'",
    # prepositions (simple + articulated)
    "di", "a", "da", "in", "con", "su", "per", "tra", "fra",
    "del", "dello", "della", "dell'", "dei", "degli", "delle",
    "al", "allo", "alla", "all'", "ai", "agli", "alle",
    "dal", "dallo", "dalla", "dall'", "dai", "dagli", "dalle",
    "nel", "nello", "nella", "nell'", "nei", "negli", "nelle",
    "sul", "sullo", "sulla", "sull'", "sui", "sugli", "sulle",
    "col", "coi",
    # conjunctions
    "e", "ed", "o", "od", "ma", "però", "che", "se", "come", "perché",
    "quando", "mentre", "anche", "né", "oppure", "quindi", "poi", "perciò",
    # pronouns / particles
    "io", "tu", "lui", "lei", "noi", "voi", "loro", "mi", "ti", "ci", "vi",
    "si", " si", "me", "te", "se", "lo", "la", "li", "le", "gli", "ne",
    "questo", "questa", "questi", "queste", "quello", "quella", "quelli", "quelle",
    "chi", "cui", "quale", "quali",
    # negation / very common adverbs & fillers
    "non", "sì", "no", "ci", "già", "ancora", "sempre", "mai", "più", "meno",
    "molto", "poco", "tutto", "tutti", "tutta", "tutte", "qui", "qua", "lì", "là",
    # common auxiliary / copula forms of essere & avere (taught in grammar)
    "è", "sono", "sei", "siamo", "siete", "era", "ero", "erano", "sia", "essere",
    "ho", "hai", "ha", "abbiamo", "avete", "hanno", "avere", "avevo", "aveva",
    # possessives (taught via grammar rule #15)
    "mio", "mia", "miei", "mie", "tuo", "tua", "tuoi", "tue",
    "suo", "sua", "suoi", "sue", "nostro", "nostra", "vostro", "vostra",
    # interjections / fillers / elided particles
    "oh", "ah", "eh", "beh", "boh", "ehi", "ok", "c'", "l'", "d'", "un'",
}


def resolve_data_dir(explicit):
    if explicit:
        return explicit
    # Reuse Fluent's own path resolver so we write alongside the learner DBs.
    hooks = os.path.join(HERE, "..", ".claude", "hooks")
    sys.path.insert(0, os.path.abspath(hooks))
    try:
        from fluent_paths import ensure_data_dir  # type: ignore
        return ensure_data_dir()
    except Exception:
        # Fallbacks mirroring the skills' documented resolution order.
        for cand in (os.environ.get("FLUENT_DATA_DIR"),
                     os.path.join(HERE, "..", "data")):
            if cand and os.path.isdir(cand):
                return os.path.abspath(cand)
        return os.path.abspath(os.path.join(HERE, "..", "data"))


def load_corpus(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_progress(data_dir):
    path = os.path.join(data_dir, PROGRESS_FILENAME)
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return {"language": "Italian", "known_words": [], "introduced_count": 0}


def save_progress(data_dir, progress):
    path = os.path.join(data_dir, PROGRESS_FILENAME)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(progress, fh, ensure_ascii=False, indent=1)
    return path


def coverage_for_known(words, known_set):
    """Highest cumulative_coverage among known words = share of text covered."""
    best = 0.0
    count = 0
    for w in words:
        if w["word"] in known_set:
            count += 1
            if w["cumulative_coverage"] > best:
                best = w["cumulative_coverage"]
    return count, best


def cmd_select(args):
    corpus = load_corpus(args.corpus)
    words = corpus["words"]
    data_dir = resolve_data_dir(args.data_dir)
    progress = load_progress(data_dir)
    known = set(progress.get("known_words", []))

    pool = words
    if args.content_only:
        pool = [w for w in words if w["word"] not in FUNCTION_WORDS]
    nxt = [w for w in pool if w["word"] not in known][: args.n]
    known_count, known_cov = coverage_for_known(words, known)
    cov_after = nxt[-1]["cumulative_coverage"] if nxt else known_cov

    checkpoints = corpus["metadata"].get("coverage_checkpoints_word_count", {})
    result = {
        "language": corpus["metadata"]["language"],
        "known_word_count": known_count,
        "known_coverage_pct": round(known_cov * 100, 1),
        "next_words": nxt,
        "coverage_after_these_pct": round(cov_after * 100, 1),
        "corpus_size": corpus["metadata"]["words_included"],
        "words_for_80pct": checkpoints.get("80%"),
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Known: {known_count} words (~{result['known_coverage_pct']}% of everyday {result['language']})")
        print(f"Next {len(nxt)} words to learn (highest frequency, not yet introduced):")
        for w in nxt:
            print(f"  #{w['rank']:>4}  {w['word']:<16} (cumulative {w['cumulative_coverage']*100:.1f}%)")
        print(f"After these you'll reach ~{result['coverage_after_these_pct']}% coverage.")
        print(f"Milestone: {result['words_for_80pct']} words = 80% of everyday {result['language']}.")


def cmd_mark(args):
    data_dir = resolve_data_dir(args.data_dir)
    progress = load_progress(data_dir)
    known = list(dict.fromkeys(progress.get("known_words", [])))  # preserve order, dedupe
    new_words = [w.strip().lower() for w in args.words.split(",") if w.strip()]
    added = [w for w in new_words if w not in known]
    known.extend(added)
    progress["known_words"] = known
    progress["introduced_count"] = len(known)
    path = save_progress(data_dir, progress)
    print(f"Marked {len(added)} new word(s) as introduced. Total known: {len(known)}.")
    print(f"Saved -> {path}")


def main():
    ap = argparse.ArgumentParser(description="Frequency-first word selector")
    ap.add_argument("--corpus", default=DEFAULT_CORPUS)
    ap.add_argument("--data-dir", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("select", help="next N words to learn + coverage")
    s.add_argument("--n", type=int, default=10)
    s.add_argument("--json", action="store_true")
    s.add_argument("--content-only", action="store_true",
                   help="skip grammatical function words (for vocab flashcard drills)")
    s.set_defaults(func=cmd_select)

    m = sub.add_parser("mark", help="record words as introduced")
    m.add_argument("--words", required=True, help="comma-separated words")
    m.set_defaults(func=cmd_mark)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
