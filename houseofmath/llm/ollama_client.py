"""Local Ollama adapter (no API key, no cloud)."""

from __future__ import annotations

import httpx


class OllamaClient:
    name = "ollama"

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3",
        timeout: float = 120.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def is_available(self) -> bool:
        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=2.0)
            r.raise_for_status()
        except (httpx.HTTPError, OSError):
            return False
        return True

    def chat(self, messages: list[dict]) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": m.get("role", "user"), "content": m.get("content", "")}
                for m in messages
            ],
            "stream": False,
        }
        try:
            r = httpx.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise RuntimeError(
                f"Could not reach Ollama at {self.base_url}. Is `ollama serve` running?"
            ) from e

        data = r.json()
        return (data.get("message") or {}).get("content", "")
