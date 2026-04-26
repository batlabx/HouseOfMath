"""Storage tests against an in-tempdir SQLite DB."""

import os
from pathlib import Path

import pytest

from houseofmath.storage import History
from houseofmath.storage.history import AttemptRow


@pytest.fixture
def history(tmp_path: Path) -> History:
    return History(db_path=tmp_path / "test.db")


def test_record_and_recall_session(history: History):
    sid = history.record_session(
        topic="algebra",
        level="easy",
        grade=6,
        score=8,
        total=10,
        duration_seconds=120,
        attempts=[
            AttemptRow(0, "alg-easy-001", 1, 1, True, ["linear-equations"]),
            AttemptRow(0, "alg-easy-002", 0, 2, False, ["one-step"]),
        ],
    )
    assert sid > 0

    recent = history.recent_sessions()
    assert recent[0].score == 8
    assert recent[0].topic == "algebra"

    attempts = history.attempts_for(sid)
    assert len(attempts) == 2
    assert attempts[0].is_correct is True
    assert attempts[1].tags == ["one-step"]


def test_lifetime_summary(history: History):
    history.record_session(topic="algebra", level="easy", grade=None, score=8, total=10, duration_seconds=60)
    history.record_session(topic="geometry", level="medium", grade=None, score=5, total=10, duration_seconds=80)
    summary = history.lifetime_summary()
    assert summary["sessions"] == 2
    assert summary["total_questions"] == 20
    assert summary["total_correct"] == 13
    assert summary["best_topic"] == "algebra"
    assert summary["weakest_topic"] == "geometry"


def test_topic_accuracy_sorted(history: History):
    history.record_session(topic="algebra", level="easy", grade=None, score=10, total=10, duration_seconds=60)
    rows = history.topic_accuracy()
    assert any(r["topic"] == "algebra" and r["accuracy"] == 1.0 for r in rows)


def test_tag_accuracy_picks_weakest_first(history: History):
    sid = history.record_session(
        topic="algebra",
        level="easy",
        grade=None,
        score=1,
        total=2,
        duration_seconds=10,
        attempts=[
            AttemptRow(0, "q1", 0, 0, True, ["alpha"]),
            AttemptRow(0, "q2", 1, 0, False, ["beta"]),
        ],
    )
    rows = history.tag_accuracy()
    assert rows[0]["tag"] == "beta"
    assert rows[0]["accuracy"] == 0.0
