"""Schema + bank-wide validator tests."""

from pathlib import Path

import pytest

from houseofmath.validation.schema import (
    Question,
    validate_bank,
    validate_file,
)

FIX_BANK = Path(__file__).parent / "fixtures" / "sample_bank"


def _q(**overrides):
    base = {
        "id": "alg-easy-001",
        "grade": 6,
        "question": "Solve $x + 1 = 2$.",
        "options": ["1", "2", "3", "4"],
        "correct": 0,
        "tags": ["linear-equations"],
        "explanation": "Subtract 1.",
        "source": "test",
        "license": "MIT",
    }
    base.update(overrides)
    return base


def test_minimal_question_validates():
    q = Question(**_q())
    assert q.id == "alg-easy-001"


def test_options_must_be_exactly_four():
    with pytest.raises(Exception):
        Question(**_q(options=["a", "b", "c"]))
    with pytest.raises(Exception):
        Question(**_q(options=["a", "b", "c", "d", "e"]))


def test_correct_index_in_range():
    with pytest.raises(Exception):
        Question(**_q(correct=4))
    with pytest.raises(Exception):
        Question(**_q(correct=-1))


def test_grade_in_range_or_null():
    Question(**_q(grade=None))
    Question(**_q(grade=3))
    Question(**_q(grade=9))
    with pytest.raises(Exception):
        Question(**_q(grade=2))
    with pytest.raises(Exception):
        Question(**_q(grade=10))


def test_explanation_required_non_empty():
    with pytest.raises(Exception):
        Question(**_q(explanation=""))


def test_tag_format():
    with pytest.raises(Exception):
        Question(**_q(tags=["Linear-Equations"]))  # uppercase
    with pytest.raises(Exception):
        Question(**_q(tags=["linear equations"]))  # whitespace


def test_validate_file_accepts_fixture():
    questions, errs = validate_file(FIX_BANK / "algebra" / "easy.json")
    assert not errs, errs
    assert len(questions) == 3


def test_validate_bank_summary_ok():
    report = validate_bank(FIX_BANK)
    assert report.ok, report.summary()
    assert report.questions_checked == 3


def test_unbalanced_latex_caught():
    bad = _q(question="Solve $x + 1 = 2.")  # missing closing $
    q = Question(**bad)
    # The Question schema doesn't reject unbalanced LaTeX directly, but the
    # file-level validator does.
    import json
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump([bad], f)
        path = Path(f.name)
    _, errs = validate_file(path)
    assert any("LaTeX" in e or "Unbalanced" in e for e in errs)
