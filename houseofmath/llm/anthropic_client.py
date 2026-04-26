"""Anthropic API adapter (separate from Claude Pro subscription)."""

from __future__ import annotations

import os


class AnthropicClient:
    name = "anthropic"

    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        api_key_env: str = "ANTHROPIC_API_KEY",
        max_tokens: int = 1024,
    ):
        self.model = model
        self.api_key_env = api_key_env
        self.max_tokens = max_tokens

    def _key(self) -> str | None:
        return os.environ.get(self.api_key_env)

    def is_available(self) -> bool:
        if not self._key():
            return False
        try:
            import anthropic  # noqa: F401, WPS433
        except ImportError:
            return False
        return True

    def chat(self, messages: list[dict]) -> str:
        if not self._key():
            raise RuntimeError(
                f"{self.api_key_env} not set. Get a key at https://console.anthropic.com "
                "and set it in your shell."
            )
        try:
            import anthropic  # noqa: WPS433
        except ImportError as e:
            raise RuntimeError(
                "Install with `pip install houseofmath[anthropic]`."
            ) from e

        client = anthropic.Anthropic(api_key=self._key())

        system_parts = [m["content"] for m in messages if m.get("role") == "system"]
        chat_msgs = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if m.get("role") in ("user", "assistant")
        ]
        if not chat_msgs:
            chat_msgs = [{"role": "user", "content": "\n\n".join(system_parts)}]
            system_parts = []

        kwargs: dict = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": chat_msgs,
        }
        if system_parts:
            kwargs["system"] = "\n\n".join(system_parts)

        resp = client.messages.create(**kwargs)
        return "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")
