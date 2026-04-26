"""Import CK-12 FlexBooks exercises.

Source: https://www.ck12.org/ (CC-BY-NC-4.0)

The NC license restriction is automatically tagged on every imported question's
`license` field so downstream consumers can filter on it.

USAGE
-----
    python scripts/importers/import_ck12.py path/to/ck12-source.json

Same expected raw schema as `import_openstax.py` — see that file for details.
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
                "id": f"{prefix}-{level}-ck12-{seq:04d}",
                "grade": r.get("grade"),
                "question": r["prompt"],
                "options": r["choices"],
                "correct": int(r["correct_idx"]),
                "tags": [t.lower().replace(" ", "-") for t in r.get("tags", [])],
                "explanation": r["explanation"],
                "source": f"ck12-{r.get('chapter', 'unknown')}",
                "license": "CC-BY-NC-4.0",
            }
        )
    return out


def write_pending(questions: list[dict]) -> None:
    by_target: dict[tuple[str, str], list[dict]] = {}
    for q in questions:
        topic_prefix = q["id"].split("-")[0]
        topic_name = next((k for k, v in PREFIX.items() if v == topic_prefix), topic_prefix)
        level = q["id"].split("-")[1]
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
    ap.add_argument("source", type=Path)
    args = ap.parse_args()

    if not args.source.exists():
        print(f"Source not found: {args.source}", file=sys.stderr)
        return 1
    raw = json.loads(args.source.read_text(encoding="utf-8"))
    questions = parse_source(raw)
    write_pending(questions)
    print(f"Imported {len(questions)} questions to {PENDING_ROOT} (CC-BY-NC-4.0)")
    print("Review each one and promote with `houseofmath promote <id>`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
