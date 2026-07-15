"""Swappable LLM layer for the triage reasoning pass.

Design goals (agreed in review):
  * Anthropic Messages API is the default provider; the interface is a
    single ``analyze(payload) -> dict | None`` method so any provider can
    be dropped in.
  * Zero third-party dependencies — stdlib urllib only, so the repo stays
    runnable by anyone with just pytest installed.
  * Graceful degradation: no ANTHROPIC_API_KEY -> HeuristicsOnlyProvider,
    and the report clearly states which mode produced it. Network or
    parse failures degrade the same way — a triage tool must never turn a
    red test run into a crashed pipeline.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Dict, Optional

from .prompts import SYSTEM_PROMPT, build_user_message

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = os.environ.get("TRIAGE_LLM_MODEL", "claude-sonnet-4-6")
_MAX_TOKENS = 4000
_TIMEOUT_S = 120


class LLMProvider:
    """Interface: return parsed analysis dict, or None if unavailable."""

    name = "abstract"

    def analyze(self, payload: Dict) -> Optional[Dict]:  # pragma: no cover
        raise NotImplementedError

    @property
    def failure_note(self) -> Optional[str]:
        return getattr(self, "_failure_note", None)


class HeuristicsOnlyProvider(LLMProvider):
    """Null provider: heuristic clustering stands alone."""

    name = "heuristics-only"

    def analyze(self, payload: Dict) -> Optional[Dict]:
        return None


class AnthropicProvider(LLMProvider):
    """Anthropic Messages API via stdlib urllib (no SDK dependency)."""

    name = "anthropic"

    def __init__(self, model: str = DEFAULT_MODEL, api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._failure_note: Optional[str] = None

    def analyze(self, payload: Dict) -> Optional[Dict]:
        if not self.api_key:
            self._failure_note = "ANTHROPIC_API_KEY not set"
            return None

        body = json.dumps(
            {
                "model": self.model,
                "max_tokens": _MAX_TOKENS,
                "temperature": 0,
                "system": SYSTEM_PROMPT,
                "messages": [
                    {
                        "role": "user",
                        "content": build_user_message(
                            json.dumps(payload, indent=1)
                        ),
                    }
                ],
            }
        ).encode()

        req = urllib.request.Request(
            ANTHROPIC_API_URL,
            data=body,
            headers={
                "content-type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:
                data = json.loads(resp.read().decode())
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            self._failure_note = f"API call failed: {exc}"
            return None
        except json.JSONDecodeError as exc:
            self._failure_note = f"non-JSON API response: {exc}"
            return None

        text = "".join(
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        )
        # Strip accidental markdown fencing before parsing.
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            self._failure_note = f"model returned unparseable JSON: {exc}"
            return None


def resolve_provider(name: str, model: str = DEFAULT_MODEL) -> LLMProvider:
    if name == "anthropic":
        provider = AnthropicProvider(model=model)
        if not provider.api_key:
            return HeuristicsOnlyProvider()
        return provider
    return HeuristicsOnlyProvider()
