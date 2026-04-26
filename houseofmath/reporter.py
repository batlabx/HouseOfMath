"""Reporter subagent — end-of-test summary.

Always shows score, time taken, and breakdown by sub-skill tag. If an LLM is
connected, also writes a personalized paragraph identifying weak areas and
suggested next topics, drawing on history.db.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .llm.base import LLMClient
from .storage.history import History
from .validation.schema import Question

REPORT_SYSTEM = (
    "You are a friendly math coach summarizing a 10-question practice test for a "
    "grades 3-9 student. Write 3-5 short sentences. Identify one or two specific "
    "sub-skills the student should review next, naming them by tag. Recommend a "
    "concrete next step (a topic + level to practice). Avoid jargon. Be encouraging."
)


@dataclass
class TestResult:
    topic: str
    level: str
    grade: int | None
    score: int
    total: int
    duration_seconds: int
    questions: list[Question]
    user_answers: list[int]

    @property
    def percent(self) -> float:
        return (self.score / self.total) * 100.0 if self.total else 0.0

    def per_question(self) -> list[dict]:
        return [
            {
                "id": q.id,
                "question": q.question,
                "options": q.options,
                "user_answer": ua,
                "correct": q.correct,
                "is_correct": ua == q.correct,
                "tags": q.tags,
                "explanation": q.explanation,
            }
            for q, ua in zip(self.questions, self.user_answers)
        ]

    def tag_breakdown(self) -> list[dict]:
        agg: dict[str, list[int]] = {}
        for q, ua in zip(self.questions, self.user_answers):
            for t in q.tags or ["(untagged)"]:
                agg.setdefault(t, [0, 0])
                agg[t][1] += 1
                if ua == q.correct:
                    agg[t][0] += 1
        out = [
            {"tag": t, "correct": c, "total": tot, "accuracy": (c / tot) if tot else 0.0}
            for t, (c, tot) in agg.items()
        ]
        out.sort(key=lambda x: x["accuracy"])
        return out


class Reporter:
    def __init__(self, client: LLMClient | None = None, history: History | None = None):
        self.client = client
        self.history = history

    def can_personalize(self) -> bool:
        return bool(self.client) and self.client.is_available() and getattr(self.client, "name", "") != "none"

    # ---------- templated (offline) ----------

    def templated_summary(self, result: TestResult) -> str:
        tb = result.tag_breakdown()
        worst = tb[0] if tb else None
        best = tb[-1] if tb else None

        lines = [
            f"You scored **{result.score}/{result.total}** ({result.percent:.0f}%) "
            f"on {result.topic} ({result.level})"
            + (f" — grade {result.grade}." if result.grade else "."),
            f"You finished in **{result.duration_seconds // 60}m {result.duration_seconds % 60}s**.",
        ]
        if worst and worst["total"] > 0 and worst["accuracy"] < 1.0:
            lines.append(
                f"Sub-skill to review: **{worst['tag']}** "
                f"({worst['correct']}/{worst['total']} correct). "
                f"Try another `{result.level}` round in `{result.topic}` and watch for these."
            )
        if best and best["accuracy"] == 1.0 and best["total"] > 0:
            lines.append(f"Strongest sub-skill this round: **{best['tag']}** — nice.")
        return " ".join(lines)

    # ---------- LLM-personalized ----------

    def personalized_summary(self, result: TestResult) -> str:
        if not self.can_personalize():
            return self.templated_summary(result)

        ctx_lines = [
            f"Score: {result.score}/{result.total} on {result.topic} ({result.level})"
            + (f", grade {result.grade}" if result.grade else ""),
            f"Time: {result.duration_seconds}s",
            "Per sub-skill (this test):",
        ]
        for row in result.tag_breakdown():
            ctx_lines.append(
                f"  - {row['tag']}: {row['correct']}/{row['total']} ({row['accuracy']:.0%})"
            )

        if self.history:
            try:
                lifetime = self.history.lifetime_summary()
                weakest = lifetime.get("weakest_topic")
                if weakest:
                    ctx_lines.append(
                        f"Lifetime context: {lifetime['sessions']} sessions, "
                        f"{lifetime['lifetime_accuracy']:.0%} accuracy overall, "
                        f"weakest topic so far: {weakest}."
                    )
            except Exception:  # noqa: BLE001
                pass

        try:
            return self.client.chat(
                [
                    {"role": "system", "content": REPORT_SYSTEM},
                    {"role": "user", "content": "\n".join(ctx_lines)},
                ]
            ).strip() or self.templated_summary(result)
        except Exception as e:  # noqa: BLE001
            return (
                f"_(LLM summary failed: {e}. Falling back to templated summary.)_\n\n"
                + self.templated_summary(result)
            )

    def summarize(self, result: TestResult) -> str:
        if self.can_personalize():
            return self.personalized_summary(result)
        return self.templated_summary(result)


def grade_user_answers(questions: Iterable[Question], user_answers: list[int]) -> int:
    """Pure inline grader (MCQ grading is not its own subagent)."""
    return sum(1 for q, ua in zip(questions, user_answers) if ua == q.correct)
