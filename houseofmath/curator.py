"""Curator subagent — deterministic question selection.

No LLM, no network. Pure stdlib + the validation schema.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

from .validation.schema import LEVELS, Question, validate_file

DEFAULT_COUNT = 10


@dataclass
class QuestionSet:
    topic: str
    level: str
    grade: int | None
    questions: list[Question] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.questions)


def list_topics(bank_root: Path) -> list[str]:
    if not bank_root.exists():
        return []
    return sorted(
        d.name
        for d in bank_root.iterdir()
        if d.is_dir() and not d.name.startswith(("_", "."))
    )


def list_levels() -> list[str]:
    return list(LEVELS)


def list_grades() -> list[int]:
    return list(range(3, 10))


def topic_matrix(bank_root: Path) -> dict[str, dict[str, int]]:
    """Return {topic: {level: count}} across the live bank."""
    matrix: dict[str, dict[str, int]] = {}
    for topic in list_topics(bank_root):
        per_level: dict[str, int] = {}
        for level in LEVELS:
            f = bank_root / topic / f"{level}.json"
            if f.exists():
                try:
                    with f.open("r", encoding="utf-8") as fh:
                        per_level[level] = len(json.load(fh))
                except (json.JSONDecodeError, OSError):
                    per_level[level] = 0
            else:
                per_level[level] = 0
        matrix[topic] = per_level
    return matrix


def _shuffle_options(q: Question, rng: random.Random) -> Question:
    """Return a copy of `q` with options shuffled and `correct` re-indexed."""
    pairs = list(enumerate(q.options))
    rng.shuffle(pairs)
    new_options = [opt for _, opt in pairs]
    new_correct = next(i for i, (orig_i, _) in enumerate(pairs) if orig_i == q.correct)
    return q.model_copy(update={"options": new_options, "correct": new_correct})


def select(
    bank_root: Path,
    topic: str,
    level: str,
    *,
    grade: int | None = None,
    count: int = DEFAULT_COUNT,
    seed: int | None = None,
    shuffle_options: bool = True,
) -> QuestionSet:
    """Sample `count` questions from `Question Bank/<topic>/<level>.json`.

    If `grade` is provided, filters to questions with that grade (questions with
    `grade=None` are always eligible). Falls back to the full pool if filtering
    leaves fewer than `count` eligible questions.
    """
    if level not in LEVELS:
        raise ValueError(f"unknown level '{level}', expected one of {LEVELS}")

    path = bank_root / topic / f"{level}.json"
    questions, errs = validate_file(path)
    if errs:
        raise ValueError(
            f"Question Bank file failed validation; cannot select questions:\n"
            + "\n".join(errs)
        )
    if not questions:
        raise ValueError(f"No questions found in {path}")

    pool: list[Question] = list(questions)
    if grade is not None:
        filtered = [q for q in pool if q.grade is None or q.grade == grade]
        if len(filtered) >= count:
            pool = filtered
        # else: fall back to the unfiltered pool to guarantee we hit `count`

    rng = random.Random(seed)
    rng.shuffle(pool)
    chosen = pool[: max(1, count)]
    if shuffle_options:
        chosen = [_shuffle_options(q, rng) for q in chosen]

    return QuestionSet(topic=topic, level=level, grade=grade, questions=chosen)
