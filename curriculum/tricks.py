#!/usr/bin/env python3
"""
Personal "tricks" cheat-sheet for the Fluent learner.

Accumulates the little rules-of-thumb the learner hits during sessions
("in for countries, a for cities"; "Svizzera the country vs svizzero the
person") into <data_dir>/tricks-db.json, so they build a personal reference
that grows with them. `/fluent-tips` displays it.

Sub-commands:
  add    Record (or reinforce) a trick. Called by the feedback formatter when a
         correction includes a generalizable rule. Dedupes by category+rule;
         re-adding an existing trick bumps its reinforced count and merges
         examples instead of duplicating.
  list   Print the cheat-sheet, grouped by category. Read by /fluent-tips.
  seed   Import the curated starter tricks (references/italian-tricks.md's JSON
         sibling) for the learner's language, skipping any they already have.

Examples:
  python3 tricks.py add --category prepositions \\
      --rule "in for countries/regions, a for cities" \\
      --example "Vivo in Svizzera" --example "Vivo a Zurigo"
  python3 tricks.py list
  python3 tricks.py list --category prepositions --json
"""
import argparse
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CURATED = os.path.join(HERE, "..", "references", "italian-tricks.json")
TRICKS_FILENAME = "tricks-db.json"


def today():
    return datetime.date.today().isoformat()


def resolve_data_dir(explicit):
    if explicit:
        return explicit
    hooks = os.path.join(HERE, "..", ".claude", "hooks")
    sys.path.insert(0, os.path.abspath(hooks))
    try:
        from fluent_paths import ensure_data_dir  # type: ignore
        return ensure_data_dir()
    except Exception:
        cand = os.environ.get("FLUENT_DATA_DIR") or os.path.join(HERE, "..", "data")
        return os.path.abspath(cand)


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48]


def load(data_dir):
    path = os.path.join(data_dir, TRICKS_FILENAME)
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return {"metadata": {"language": "Italian", "total_tricks": 0}, "tricks": []}


def save(data_dir, doc):
    doc["metadata"]["total_tricks"] = len(doc["tricks"])
    doc["metadata"]["last_updated"] = today()
    path = os.path.join(data_dir, TRICKS_FILENAME)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    return path


def _find(tricks, category, rule):
    key = (category.lower().strip(), rule.lower().strip())
    for t in tricks:
        if (t.get("category", "").lower().strip(), t.get("rule", "").lower().strip()) == key:
            return t
    return None


def add_trick(doc, category, rule, examples, source=None):
    existing = _find(doc["tricks"], category, rule)
    if existing:
        existing["times_reinforced"] = existing.get("times_reinforced", 1) + 1
        existing["last_seen"] = today()
        for ex in examples:
            if ex and ex not in existing["examples"]:
                existing["examples"].append(ex)
        return existing, False
    trick = {
        "id": slugify(f"{category}-{rule}"),
        "category": category,
        "rule": rule,
        "examples": [e for e in examples if e],
        "learned_date": today(),
        "last_seen": today(),
        "times_reinforced": 1,
        "source": source or "session",
    }
    doc["tricks"].append(trick)
    return trick, True


def cmd_add(args, data_dir):
    doc = load(data_dir)
    _, created = add_trick(doc, args.category, args.rule, args.example or [], args.source)
    save(data_dir, doc)
    print(f"{'Added' if created else 'Reinforced'} trick: [{args.category}] {args.rule}")


def cmd_list(args, data_dir):
    doc = load(data_dir)
    tricks = doc["tricks"]
    if args.category:
        tricks = [t for t in tricks if t["category"].lower() == args.category.lower()]

    if args.json:
        print(json.dumps({"metadata": doc["metadata"], "tricks": tricks}, ensure_ascii=False, indent=2))
        return

    if not tricks:
        print("No tricks yet — they'll appear here as you learn them in sessions.")
        return

    by_cat = {}
    for t in tricks:
        by_cat.setdefault(t["category"], []).append(t)

    print(f"🧠 Your Italian Cheat-Sheet — {len(tricks)} trick(s)\n")
    for cat in sorted(by_cat):
        print(f"## {cat.replace('_', ' ').title()}")
        for t in by_cat[cat]:
            star = " ⭐" if t.get("times_reinforced", 1) >= 3 else ""
            print(f"  • {t['rule']}{star}")
            for ex in t["examples"][:3]:
                print(f"      – {ex}")
        print()


def cmd_seed(args, data_dir):
    if not os.path.isfile(CURATED):
        sys.exit(f"No curated file at {CURATED}")
    with open(CURATED, encoding="utf-8") as fh:
        curated = json.load(fh)
    doc = load(data_dir)
    added = 0
    for t in curated.get("tricks", []):
        _, created = add_trick(doc, t["category"], t["rule"], t.get("examples", []), source="curated")
        added += int(created)
    save(data_dir, doc)
    print(f"Seeded {added} new curated trick(s). Total: {len(doc['tricks'])}.")


def main():
    ap = argparse.ArgumentParser(description="Fluent personal tricks cheat-sheet")
    ap.add_argument("--data-dir", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add")
    a.add_argument("--category", required=True)
    a.add_argument("--rule", required=True)
    a.add_argument("--example", action="append", help="repeatable")
    a.add_argument("--source", default=None)
    a.set_defaults(func=cmd_add)

    l = sub.add_parser("list")
    l.add_argument("--category", default=None)
    l.add_argument("--json", action="store_true")
    l.set_defaults(func=cmd_list)

    s = sub.add_parser("seed")
    s.set_defaults(func=cmd_seed)

    args = ap.parse_args()
    data_dir = resolve_data_dir(args.data_dir)
    args.func(args, data_dir)


if __name__ == "__main__":
    main()
