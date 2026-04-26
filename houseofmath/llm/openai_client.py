"""OpenAI API adapter.

Note: ChatGPT Plus / Pro subscriptions do NOT grant API access — these are
separate products. Users need a paid API key at platform.openai.com.
"""

from __future__ import annotations

import os


class OpenAIClient:
    name = "openai"

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key_env: str = "OPENAI_API_KEY",
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
            import openai  # noqa: F401, WPS433
        except ImportError:
            return False
        return True

    def chat(self, messages: list[dict]) -> str:
        if not self._key():
            raise RuntimeError(
                f"{self.api_key_env} not set. Get a key at https://platform.openai.com/api-keys."
            )
        try:
            import openai  # noqa: WPS433
        except ImportError as e:
            raise RuntimeError(
                "Install with `pip install houseofmath[openai]`."
            ) from e

        client = openai.OpenAI(api_key=self._key())
        resp = client.chat.completions.create(
            model=self.model,
            messages=[{"role": m["role"], "content": m["content"]} for m in messages],
            max_tokens=self.max_tokens,
        )
        return resp.choices[0].message.content or ""
