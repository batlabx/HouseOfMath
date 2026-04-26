"""Subscription-auth path: shells out to the user's Claude Code CLI."""

from __future__ import annotations

import shutil
import subprocess


class ClaudeCodeClient:
    """Use the locally installed `claude` CLI as the LLM.

    The user runs `claude /login` once (handled by Claude Code itself) and the
    subscription auth is persisted. HouseOfMath never sees or stores the user's
    credentials.
    """

    name = "claude-code"

    def __init__(self, binary: str = "claude", model: str | None = None, timeout: int = 90):
        self.binary = binary
        self.model = model
        self.timeout = timeout

    def is_available(self) -> bool:
        return shutil.which(self.binary) is not None

    def chat(self, messages: list[dict]) -> str:
        if not self.is_available():
            raise RuntimeError(
                f"Claude Code CLI not found on PATH (looking for `{self.binary}`). "
                "Install it from https://docs.claude.com/en/docs/agents-and-tools/claude-code/overview "
                "and run `claude /login`."
            )
        prompt = "\n\n".join(m.get("content", "") for m in messages if m.get("content"))
        cmd = [self.binary, "-p", prompt]
        if self.model:
            cmd.extend(["--model", self.model])
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=True,
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"Claude Code CLI timed out after {self.timeout}s") from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Claude Code CLI failed (exit {e.returncode}): {e.stderr.strip()}"
            ) from e
        return result.stdout.strip()
