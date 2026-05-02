#!/usr/bin/env python3
"""
Escape unbalanced currency `$` signs in HouseOfMath Question Bank entries.

The validator (houseofmath/validation/schema.py::_basic_latex_balance) strips
`\\$` and then requires an even number of `$` chars. Question authors often write
literal dollar amounts ("$1050", "$22") which are odd-count and trip the check.

This script walks every question. For each text field (question, explanation,
options) where the unescaped `$` count is odd, it escapes all unescaped `$`
characters as `\\$`. Already-escaped `\\$` are left alone.

Run from the repo root:
    python3 fix_latex.py
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

QB_DIR = Path("Question Bank")
UNESCAPED_DOLLAR = re.compile(r"(?<!\\)\$")


def needs_fix(text: str) -> bool:
    """Mirror the validator: strip `\\$` then require even count."""
    return text.replace("\\$", "").count("$") % 2 != 0


def fix(text: str) -> str:
    """Escape every unescaped `$` so the validator strips them out."""
    return UNESCAPED_DOLLAR.sub(r"\\$", text)


def fix_question(q: dict) -> int:
    changed = 0
    for key in ("question", "explanation"):
        v = q.get(key)
        if isinstance(v, str) and needs_fix(v):
            q[key] = fix(v)
            changed += 1
    opts = q.get("options")
    if isinstance(opts, list):
        for i, o in enumerate(opts):
            if isinstance(o, str) and needs_fix(o):
                opts[i] = fix(o)
                changed += 1
    return changed


def main() -> int:
    if not QB_DIR.is_dir():
        print(f"error: '{QB_DIR}' not found. Run this from the repo root.", file=sys.stderr)
        return 1

    total_files = 0
    total_questions = 0
    total_fields = 0

    for path in sorted(QB_DIR.rglob("*.json")):
        with path.open() as f:
            data = json.load(f)
        if not isinstance(data, list):
            continue

        file_questions = 0
        file_fields = 0
        for i, q in enumerate(data):
            if not isinstance(q, dict):
                continue
            n = fix_question(q)
            if n:
                print(f"  {path}[{i}] id={q.get('id')}: fixed {n} field(s)")
                file_questions += 1
                file_fields += n

        if file_questions:
            with path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")
            total_files += 1
            total_questions += file_questions
            total_fields += file_fields

    print(f"\nFixed {total_fields} field(s) across {total_questions} question(s) "
          f"in {total_files} file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
