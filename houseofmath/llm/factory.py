"""Provider lookup + auto-detection used by `houseofmath init`."""

from __future__ import annotations

import os
import shutil
from typing import Any

from .base import LLMClient

PROVIDERS = ("none", "claude-code", "gemini", "ollama", "anthropic", "openai")


def get_client(cfg: dict[str, Any]) -> LLMClient:
    """Instantiate the configured adapter from a parsed config dict."""
    provider = cfg.get("provider", "none")

    if provider == "none":
        from .none_client import NoneClient

        return NoneClient()

    if provider == "claude-code":
        from .claude_code_client import ClaudeCodeClient

        block = cfg.get("claude-code", {}) or {}
        return ClaudeCodeClient(
            binary=block.get("binary", "claude"),
            model=block.get("model"),
        )

    if provider == "anthropic":
        from .anthropic_client import AnthropicClient

        block = cfg.get("anthropic", {}) or {}
        return AnthropicClient(
            model=block.get("model", "claude-sonnet-4-6"),
            api_key_env=block.get("api_key_env", "ANTHROPIC_API_KEY"),
        )

    if provider == "openai":
        from .openai_client import OpenAIClient

        block = cfg.get("openai", {}) or {}
        return OpenAIClient(
            model=block.get("model", "gpt-4o-mini"),
            api_key_env=block.get("api_key_env", "OPENAI_API_KEY"),
        )

    if provider == "gemini":
        from .gemini_client import GeminiClient

        block = cfg.get("gemini", {}) or {}
        return GeminiClient(
            model=block.get("model", "gemini-2.0-flash"),
            api_key_env=block.get("api_key_env", "GOOGLE_AI_API_KEY"),
        )

    if provider == "ollama":
        from .ollama_client import OllamaClient

        block = cfg.get("ollama", {}) or {}
        return OllamaClient(
            base_url=block.get("base_url", "http://localhost:11434"),
            model=block.get("model", "llama3"),
        )

    raise ValueError(f"Unknown provider '{provider}'. Expected one of {PROVIDERS}")


def autodetect() -> str:
    """Probe the environment and recommend the highest-value available provider.

    Order matches section 7.5 of the build instructions.
    """
    if shutil.which("claude"):
        return "claude-code"

    try:
        import httpx  # local import keeps factory cheap

        r = httpx.get("http://localhost:11434/api/tags", timeout=1.0)
        if r.status_code == 200:
            return "ollama"
    except Exception:  # noqa: BLE001
        pass

    if os.environ.get("GOOGLE_AI_API_KEY"):
        return "gemini"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"

    return "none"
