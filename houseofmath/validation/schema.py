"""Pydantic schema for Question Bank entries + bank-wide validators."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel, Field, ValidationError, field_validator

LEVELS = ("easy", "medium", "difficult")
GRADE_MIN, GRADE_MAX = 3, 9


class Question(BaseModel):
    """One MCQ question."""

    id: str = Field(..., min_length=1)
    grade: int | None = None
    question: str = Field(..., min_length=1)
    options: list[str]
    correct: int
    tags: list[str] = Field(default_factory=list)
    explanation: str = Field(..., min_length=1)
    source: str | None = None
    license: str | None = None

    @field_validator("options")
    @classmethod
    def _options_len(cls, v: list[str]) -> list[str]:
        if len(v) != 4:
            raise ValueError(f"options must have exactly 4 entries, got {len(v)}")
        if any(not (isinstance(o, str) and o.strip()) for o in v):
            raise ValueError("each option must be a non-empty string")
        return v

    @field_validator("correct")
    @classmethod
    def _correct_in_range(cls, v: int) -> int:
        if not (0 <= v <= 3):
            raise ValueError(f"correct must be in [0, 3], got {v}")
        return v

    @field_validator("grade")
    @classmethod
    def _grade_in_range(cls, v: int | None) -> int | None:
        if v is None:
            return v
        if not (GRADE_MIN <= v <= GRADE_MAX):
            raise ValueError(f"grade must be null or in [{GRADE_MIN}, {GRADE_MAX}], got {v}")
        return v

    @field_validator("tags")
    @classmethod
    def _tags_format(cls, v: list[str]) -> list[str]:
        for t in v:
            if not t or any(c.isspace() for c in t) or t != t.lower():
                raise ValueError(
                    f"tag '{t}' must be lowercase and contain no whitespace (use hyphens)"
                )
        return v


@dataclass
class ValidationReport:
    files_checked: int = 0
    questions_checked: int = 0
    errors: list[str] = field(default_factory=list)
    duplicate_ids: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors and not self.duplicate_ids

    def summary(self) -> str:
        if self.ok:
            return (
                f"OK — {self.questions_checked} questions across "
                f"{self.files_checked} files."
            )
        lines = [f"FAIL — {len(self.errors)} error(s) across {self.files_checked} files."]
        if self.duplicate_ids:
            lines.append(f"Duplicate IDs: {', '.join(self.duplicate_ids)}")
        for e in self.errors:
            lines.append(f"  - {e}")
        return "\n".join(lines)


def _check_latex(text: str) -> str | None:
    """Return an error message, or None if OK."""
    try:
        from pylatexenc.latex2text import LatexNodes2Text  # noqa: WPS433
    except ImportError:
        # Soft-skip if pylatexenc isn't installed; basic balance check still runs.
        return _basic_latex_balance(text)

    try:
        LatexNodes2Text().latex_to_text(text)
    except Exception as e:  # noqa: BLE001
        return f"LaTeX parse error: {e}"
    return _basic_latex_balance(text)


def _basic_latex_balance(text: str) -> str | None:
    # Count $ delimiters but ignore \$ (escaped dollars — these are literal $ chars,
    # not LaTeX delimiters). Also ignore $$ block delimiters by treating them as a pair.
    stripped = text.replace("\\$", "")
    # $$...$$ pairs count as two delimiters; collapse them.
    # Net: just count single `$` after removing escaped ones.
    if stripped.count("$") % 2 != 0:
        return "Unbalanced `$` delimiters in LaTeX (after ignoring escaped \\$)"
    return None


def _validate_question_obj(raw: dict, file: Path, idx: int) -> tuple[Question | None, list[str]]:
    errs: list[str] = []
    try:
        q = Question(**raw)
    except ValidationError as e:
        for err in e.errors():
            loc = ".".join(str(p) for p in err["loc"])
            errs.append(f"{file}[{idx}]: {loc}: {err['msg']}")
        return None, errs

    for field_name in ("question", "explanation"):
        msg = _check_latex(getattr(q, field_name))
        if msg:
            errs.append(f"{file}[{idx}] id={q.id}: {field_name}: {msg}")
    for i, opt in enumerate(q.options):
        msg = _check_latex(opt)
        if msg:
            errs.append(f"{file}[{idx}] id={q.id}: options[{i}]: {msg}")

    return q, errs


def validate_file(path: Path) -> tuple[list[Question], list[str]]:
    if not path.exists():
        return [], [f"{path}: file not found"]
    try:
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        return [], [f"{path}: invalid JSON: {e}"]

    if not isinstance(raw, list):
        return [], [f"{path}: top-level must be a list, got {type(raw).__name__}"]

    questions: list[Question] = []
    errors: list[str] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            errors.append(f"{path}[{i}]: each entry must be an object")
            continue
        q, errs = _validate_question_obj(item, path, i)
        errors.extend(errs)
        if q:
            questions.append(q)
    return questions, errors


def _iter_bank_files(bank_root: Path) -> Iterable[Path]:
    for topic_dir in sorted(bank_root.iterdir()):
        if not topic_dir.is_dir() or topic_dir.name.startswith("_") or topic_dir.name.startswith("."):
            continue
        for level in LEVELS:
            f = topic_dir / f"{level}.json"
            if f.exists():
                yield f


def validate_bank(bank_root: Path) -> ValidationReport:
    report = ValidationReport()
    seen_ids: dict[str, Path] = {}

    if not bank_root.exists():
        report.errors.append(f"Question Bank directory not found: {bank_root}")
        return report

    for path in _iter_bank_files(bank_root):
        report.files_checked += 1
        questions, errs = validate_file(path)
        report.errors.extend(errs)
        for q in questions:
            report.questions_checked += 1
            if q.id in seen_ids:
                report.duplicate_ids.append(f"{q.id} ({seen_ids[q.id]} & {path})")
            else:
                seen_ids[q.id] = path
    return report
