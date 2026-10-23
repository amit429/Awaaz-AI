"""Mocks for MOCK_PROVIDERS=true: a scripted fake callee, silent TTS and fixture LLM output."""

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

SPECS_DIR = Path(__file__).resolve().parents[4] / "specs"


class FakeCallee:
    """Plays the other person from specs/fixtures/callee_*.json (text only).

    The first line is spoken when the call connects. Each later user turn advances
    the script; a user turn matching `repeat_on` repeats the current line instead.
    """

    def __init__(self, script: dict[str, Any]) -> None:
        self.script = script
        self.lines: list[dict[str, Any]] = script["lines"]
        self._repeat_on = [p.lower() for p in script.get("repeat_on", [])]
        self._i = -1

    @classmethod
    def from_fixture(cls, name: str, specs_dir: Path = SPECS_DIR) -> "FakeCallee":
        path = specs_dir / "fixtures" / f"callee_{name}.json"
        return cls(json.loads(path.read_text(encoding="utf-8")))

    @property
    def done(self) -> bool:
        return self._i >= len(self.lines) - 1

    def current(self) -> dict[str, Any] | None:
        return self.lines[self._i] if 0 <= self._i < len(self.lines) else None

    def opening(self) -> dict[str, Any]:
        self._i = 0
        return self.lines[0]

    def reply_to(self, user_text: str) -> dict[str, Any] | None:
        """Next line after a user turn, or None when the script has ended."""
        if self._i < 0:
            return self.opening()
        lowered = user_text.lower()
        if any(p in lowered for p in self._repeat_on) and self.current():
            return self.current()
        if self.done:
            return None
        self._i += 1
        return self.lines[self._i]


class MockTts:
    async def synthesize(
        self, text: str, *, voice_id: str, lang: str, rate: float = 1.0
    ) -> AsyncIterator[bytes]:
        yield b"\x00\x00" * 320  # one 20 ms frame of silence at 16 kHz


class MockLlm:
    """Returns canned JSON keyed by a marker in the prompt; empty dict if none match."""

    def __init__(self, canned: dict[str, dict[str, Any]] | None = None) -> None:
        self.canned = canned or {}

    async def complete_json(self, prompt: str, *, schema: dict[str, Any]) -> dict[str, Any]:
        for marker, out in self.canned.items():
            if marker in prompt:
                return out
        return {}


class MockTelephony:
    def __init__(self) -> None:
        self.hungup: list[str] = []

    async def start_call(self, *, to: str, leg_id: str) -> str:
        return f"mock-{leg_id}"

    async def hangup(self, provider_call_id: str) -> None:
        self.hungup.append(provider_call_id)
