"""Google AI Studio Gemini adapter (free tier)."""

from __future__ import annotations

import os


class GeminiClient:
    name = "gemini"

    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        api_key_env: str = "GOOGLE_AI_API_KEY",
    ):
        self.model = model
        self.api_key_env = api_key_env

    def _key(self) -> str | None:
        return os.environ.get(self.api_key_env)

    def is_available(self) -> bool:
        if not self._key():
            return False
        try:
            import google.generativeai  # noqa: F401, WPS433
        except ImportError:
            return False
        return True

    def chat(self, messages: list[dict]) -> str:
        if not self._key():
            raise RuntimeError(
                f"{self.api_key_env} not set. Get a free key at https://aistudio.google.com."
            )
        try:
            import google.generativeai as genai  # noqa: WPS433
        except ImportError as e:
            raise RuntimeError(
                "Install with `pip install houseofmath[gemini]`."
            ) from e

        genai.configure(api_key=self._key())
        model = genai.GenerativeModel(self.model)
        prompt = "\n\n".join(
            f"{m.get('role', 'user').upper()}: {m.get('content', '')}" for m in messages
        )
        resp = model.generate_content(prompt)
        return getattr(resp, "text", "") or ""
