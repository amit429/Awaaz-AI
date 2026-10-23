"""Provider interfaces. Live adapters and mocks implement these; relay code imports only these."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class SttEvent:
    text: str
    final: bool
    lang: str | None = None
    confidence: float | None = None


class Stt(Protocol):
    """One streaming transcription session. Audio in is PCM16 mono at `sample_rate`."""

    async def send_audio(self, pcm: bytes) -> None: ...
    def events(self) -> AsyncIterator[SttEvent]: ...
    async def close(self) -> None: ...


class Tts(Protocol):
    """Yields PCM16 mono 16 kHz chunks."""

    def synthesize(
        self, text: str, *, voice_id: str, lang: str, rate: float = 1.0
    ) -> AsyncIterator[bytes]: ...


class Llm(Protocol):
    """Returns a JSON object. Callers validate it against their own schema."""

    async def complete_json(self, prompt: str, *, schema: dict[str, Any]) -> dict[str, Any]: ...


class Telephony(Protocol):
    async def start_call(self, *, to: str, leg_id: str) -> str:
        """Place an outbound call; returns the provider call id."""

    async def hangup(self, provider_call_id: str) -> None: ...
