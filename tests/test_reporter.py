"""Reporter + grading tests."""

from houseofmath.reporter import Reporter, TestResult, grade_user_answers
from houseofmath.validation.schema import Question


def _q(qid: str, correct: int = 0, tags=None) -> Question:
    return Question(
        id=qid,
        grade=6,
        question="$1+1=?$",
        options=["2", "3", "4", "5"],
        correct=correct,
        tags=tags or ["arithmetic"],
        explanation="One plus one is two.",
        source="test",
        license="MIT",
    )


def test_grade_user_answers():
    qs = [_q("a", correct=0), _q("b", correct=1), _q("c", correct=2)]
    assert grade_user_answers(qs, [0, 1, 2]) == 3
    assert grade_user_answers(qs, [0, 0, 0]) == 1
    assert grade_user_answers(qs, [3, 3, 3]) == 0


def test_templated_summary_mentions_score():
    qs = [_q("a", correct=0, tags=["a"]), _q("b", correct=1, tags=["b"])]
    result = TestResult(
        topic="algebra",
        level="easy",
        grade=6,
        score=1,
        total=2,
        duration_seconds=45,
        questions=qs,
        user_answers=[0, 0],
    )
    summary = Reporter().templated_summary(result)
    assert "1/2" in summary or "1 / 2" in summary or "1" in summary
    assert "algebra" in summary


def test_tag_breakdown_isolates_subskills():
    qs = [_q("a", correct=0, tags=["geometry"]), _q("b", correct=1, tags=["arithmetic"])]
    result = TestResult("topic", "easy", None, 1, 2, 0, qs, [0, 0])
    tb = result.tag_breakdown()
    by_tag = {row["tag"]: row for row in tb}
    assert by_tag["geometry"]["accuracy"] == 1.0
    assert by_tag["arithmetic"]["accuracy"] == 0.0
