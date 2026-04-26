"""No-op LLM adapter — used when `provider: none`."""

from __future__ import annotations


class NoneClient:
    """Always-available no-op adapter.

    `chat()` raises `RuntimeError` so callers can detect they should use the
    static fallback. Use `is_available()` and the higher-level guards in
    `tutor`/`reporter` to avoid ever calling `chat()` on this.
    """

    name = "none"

    def is_available(self) -> bool:
        return True

    def chat(self, messages: list[dict]) -> str:
        raise RuntimeError(
            "LLM provider is set to 'none'. Run `houseofmath init` to connect a provider."
        )
