"""LLMClient protocol — every adapter implements this."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    """Minimal contract for an LLM provider adapter.

    All adapters must implement these two methods. Adding a new provider is one
    file (~30 lines) implementing this protocol plus one entry in
    `houseofmath.llm.factory.PROVIDERS`.
    """

    def chat(self, messages: list[dict]) -> str:
        """Take a list of {role, content} dicts and return a single string."""
        ...

    def is_available(self) -> bool:
        """Return True if this provider is reachable / authenticated right now."""
        ...
