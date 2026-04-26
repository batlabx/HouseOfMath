"""Import OpenStax PreAlgebra / Elementary Algebra exercises.

Source: https://openstax.org/details/books/prealgebra-2e (CC-BY-4.0)

This script writes candidate questions to `Question Bank/_pending/<topic>/<level>.json`.
Importers never write to the live bank — a maintainer must `houseofmath promote <id>`
each question after review.

USAGE
-----
    python scripts/importers/import_openstax.py path/to/openstax-source.json

The expected source format is a JSON array of objects with at minimum:
  - `chapter`     : str
  - `topic`       : "algebra" | "arithmetic" | ...
  - `level`       : "easy" | "medium" | "difficult"
  - `grade`       : int | null
  - `prompt`      : str (the question text, may contain LaTeX)
  - `choices`     : list[str] (4)
  - `correct_idx` : int
  - `explanation` : str
  - `tags`        : list[str]

Adapt `parse_source()` to whatever raw format you have.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PENDING_ROOT = REPO_ROOT / "Question Bank" / "_pending"

PREFIX = {
    "algebra": "alg",
    "arithmetic": "arith",
    "geometry": "geo",
    "fractions": "frac",
    "percentages": "pct",
}


def parse_source(raw: list[dict]) -> list[dict]:
    out: list[dict] = []
    for i, r in enumerate(raw):
        topic = r["topic"].lower()
        level = r["level"].lower()
        prefix = PREFIX.get(topic, topic[:4])
        seq = i + 1
        out.append(
            {
                "id": f"{prefix}-{level}-openstax-{seq:04d}",
                "grade": r.get("grade"),
                "question": r["prompt"],
                "options": r["choices"],
                "correct": int(r["correct_idx"]),
                "tags": [t.lower().replace(" ", "-") for t in r.get("tags", [])],
                "explanation": r["explanation"],
                "source": f"openstax-{r.get('chapter', 'unknown')}",
                "license": "CC-BY-4.0",
            }
        )
    return out


def write_pending(questions: list[dict]) -> None:
    by_target: dict[tuple[str, str], list[dict]] = {}
    for q in questions:
        topic = q["id"].split("-")[0]
        topic_name = next((k for k, v in PREFIX.items() if v == topic), topic)
        # Reverse-derive level from id; structure is `<prefix>-<level>-...`
        parts = q["id"].split("-")
        level = parts[1]
        by_target.setdefault((topic_name, level), []).append(q)

    for (topic_name, level), qs in by_target.items():
        out_dir = PENDING_ROOT / topic_name
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{level}.json"
        existing = []
        if out_file.exists():
            existing = json.loads(out_file.read_text(encoding="utf-8"))
        existing_ids = {e.get("id") for e in existing}
        merged = existing + [q for q in qs if q["id"] not in existing_ids]
        out_file.write_text(json.dumps(merged, indent=2), encoding="utf-8")
        print(f"  wrote {len(qs)} -> {out_file} ({len(merged)} total pending)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", type=Path, help="Path to a normalized OpenStax JSON dump")
    args = ap.parse_args()

    if not args.source.exists():
        print(f"Source not found: {args.source}", file=sys.stderr)
        return 1
    raw = json.loads(args.source.read_text(encoding="utf-8"))
    questions = parse_source(raw)
    write_pending(questions)
    print(f"Imported {len(questions)} questions to {PENDING_ROOT}")
    print("Review each one and promote with `houseofmath promote <id>`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
