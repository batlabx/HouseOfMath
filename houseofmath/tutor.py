"""Tutor subagent — explanation rephrasing.

Uses the static `explanation` shipped with each question by default. If an LLM
provider is connected, can rephrase the explanation in simpler/different
wording on user request ("Explain it differently"). Falls back gracefully when
provider is `none`.
"""

from __future__ import annotations

from .llm.base import LLMClient
from .validation.schema import Question

REPHRASE_SYSTEM = (
    "You are a patient math tutor for a student in grades 3-9. "
    "When given a multiple-choice question, the correct answer, and the "
    "current explanation, write a NEW explanation in plain, friendly language. "
    "Use a different angle or analogy from the original. "
    "Render math with LaTeX ($...$ inline, $$...$$ block). "
    "Keep it to 4-6 sentences. Do not invent new facts; only re-explain."
)


class Tutor:
    def __init__(self, client: LLMClient | None = None):
        self.client = client

    def static_explanation(self, q: Question) -> str:
        return q.explanation

    def can_rephrase(self) -> bool:
        return bool(self.client) and self.client.is_available() and getattr(self.client, "name", "") != "none"

    def rephrase(self, q: Question) -> str:
        """Return a re-worded explanation. Falls back to the static text on any error."""
        if not self.can_rephrase():
            return self.static_explanation(q)

        correct_text = q.options[q.correct]
        user_msg = (
            f"Question: {q.question}\n"
            f"Options:\n"
            + "\n".join(f"  {chr(65 + i)}) {opt}" for i, opt in enumerate(q.options))
            + f"\nCorrect answer: {chr(65 + q.correct)}) {correct_text}\n"
            f"Current explanation: {q.explanation}\n\n"
            "Please rewrite the explanation in a different way."
        )
        try:
            return self.client.chat(
                [
                    {"role": "system", "content": REPHRASE_SYSTEM},
                    {"role": "user", "content": user_msg},
                ]
            ).strip() or self.static_explanation(q)
        except Exception as e:  # noqa: BLE001
            return f"_(LLM rephrase failed: {e}. Falling back to original explanation.)_\n\n{q.explanation}"
