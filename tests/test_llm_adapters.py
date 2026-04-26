"""Smoke tests for every LLM adapter — verify they implement the contract."""

import os

import pytest

from houseofmath.llm.base import LLMClient
from houseofmath.llm.anthropic_client import AnthropicClient
from houseofmath.llm.claude_code_client import ClaudeCodeClient
from houseofmath.llm.factory import PROVIDERS, get_client
from houseofmath.llm.gemini_client import GeminiClient
from houseofmath.llm.none_client import NoneClient
from houseofmath.llm.ollama_client import OllamaClient
from houseofmath.llm.openai_client import OpenAIClient


@pytest.mark.parametrize(
    "client",
    [
        NoneClient(),
        ClaudeCodeClient(),
        AnthropicClient(api_key_env="__DEFINITELY_NOT_SET__"),
        OpenAIClient(api_key_env="__DEFINITELY_NOT_SET__"),
        GeminiClient(api_key_env="__DEFINITELY_NOT_SET__"),
        OllamaClient(base_url="http://127.0.0.1:1"),
    ],
)
def test_implements_protocol(client):
    assert isinstance(client, LLMClient)
    assert hasattr(client, "is_available")
    # is_available must never raise on a happy environment
    client.is_available()


def test_factory_recognizes_all_providers():
    assert set(PROVIDERS) == {
        "none",
        "claude-code",
        "gemini",
        "ollama",
        "anthropic",
        "openai",
    }


def test_factory_returns_none_client_for_none_provider():
    c = get_client({"provider": "none"})
    assert isinstance(c, NoneClient)
    assert c.is_available()


def test_none_client_chat_raises():
    with pytest.raises(RuntimeError):
        NoneClient().chat([{"role": "user", "content": "hi"}])


def test_factory_raises_on_unknown_provider():
    with pytest.raises(ValueError):
        get_client({"provider": "telepathy"})


def test_anthropic_chat_without_key_raises():
    os.environ.pop("__DEFINITELY_NOT_SET__", None)
    c = AnthropicClient(api_key_env="__DEFINITELY_NOT_SET__")
    assert not c.is_available()
    with pytest.raises(RuntimeError):
        c.chat([{"role": "user", "content": "hi"}])
