"""Curator tests."""

from pathlib import Path

import pytest

from houseofmath.curator import select, list_topics, topic_matrix

FIX_BANK = Path(__file__).parent / "fixtures" / "sample_bank"


def test_list_topics():
    assert list_topics(FIX_BANK) == ["algebra"]


def test_topic_matrix():
    matrix = topic_matrix(FIX_BANK)
    assert matrix["algebra"]["easy"] == 3
    assert matrix["algebra"]["medium"] == 0


def test_select_returns_requested_count():
    qset = select(FIX_BANK, "algebra", "easy", count=2, seed=1)
    assert qset.total == 2
    assert qset.topic == "algebra"
    assert qset.level == "easy"


def test_select_caps_at_pool_size():
    qset = select(FIX_BANK, "algebra", "easy", count=100, seed=1)
    assert qset.total == 3


def test_select_seed_is_deterministic():
    a = select(FIX_BANK, "algebra", "easy", count=2, seed=42)
    b = select(FIX_BANK, "algebra", "easy", count=2, seed=42)
    assert [q.id for q in a.questions] == [q.id for q in b.questions]


def test_select_grade_filter_falls_back_when_pool_too_small():
    # No grade-12 questions exist, but we still want 2 back.
    qset = select(FIX_BANK, "algebra", "easy", grade=8, count=2, seed=1)
    assert qset.total == 2


def test_unknown_level_raises():
    with pytest.raises(ValueError):
        select(FIX_BANK, "algebra", "extreme", count=1)


def test_options_shuffle_keeps_correct_index_consistent():
    qset = select(FIX_BANK, "algebra", "easy", count=3, seed=7, shuffle_options=True)
    for q in qset.questions:
        # The correct index must still point to a real option.
        assert 0 <= q.correct <= 3
        assert q.options[q.correct] is not None
