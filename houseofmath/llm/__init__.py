"""LLM adapter layer (BYO-LLM)."""

from .base import LLMClient
from .factory import PROVIDERS, get_client

__all__ = ["LLMClient", "PROVIDERS", "get_client"]
