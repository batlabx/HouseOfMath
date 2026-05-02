#!/usr/bin/env python3
"""
Normalize tags across the HouseOfMath Question Bank.

Tag rule (from houseofmath/validation/schema.py):
    tags must be lowercase and contain no whitespace (use hyphens).

Run from the repo root:
    python fix_tags.py
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

QB_DIR = Path("Question Bank")


def normalize(tag: str) -> str:
    return re.sub(r"\s+", "-", tag.strip()).lower()


def main() -> int:
    if not QB_DIR.is_dir():
        print(f"error: '{QB_DIR}' not found. Run this from the repo root.", file=sys.stderr)
        return 1

    total_files = 0
    total_changes = 0

    for path in sorted(QB_DIR.rglob("*.json")):
        with path.open() as f:
            data = json.load(f)
        if not isinstance(data, list):
            continue

        file_changes = 0
        for i, q in enumerate(data):
            tags = q.get("tags")
            if not isinstance(tags, list):
                continue
            new_tags = []
            for t in tags:
                if not isinstance(t, str):
                    new_tags.append(t)
                    continue
                n = normalize(t)
                if n != t:
                    print(f"  {path}[{i}]: {t!r} -> {n!r}")
                    file_changes += 1
                new_tags.append(n)
            q["tags"] = new_tags

        if file_changes:
            with path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")
            total_files += 1
            total_changes += file_changes

    print(f"\nFixed {total_changes} tag(s) across {total_files} file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
