"""Twilio WhatsApp sandbox: sending, signature validation and payload normalisation."""

import asyncio
import base64
import hashlib
import hmac
import time
from dataclasses import dataclass, field
from typing import Protocol

import httpx

from app.config import Settings


@dataclass
class Inbound:
    wa_id: str  # E.164 without "+"
    type: str  # text | audio | image | other
    text: str = ""
    name: str | None = None
    media_url: str | None = None
    message_id: str | None = None


class WaSender(Protocol):
    async def send(self, wa_id: str, text: str) -> None: ...


@dataclass
class LogSender:
    """Collects outgoing messages (dev and tests)."""

    outbox: list[tuple[str, str]] = field(default_factory=list)

    async def send(self, wa_id: str, text: str) -> None:
        self.outbox.append((wa_id, text))

    def texts(self, wa_id: str | None = None) -> list[str]:
        return [t for w, t in self.outbox if wa_id is None or w == wa_id]


class TwilioSandboxSender:
    """Sends through the Twilio API. The sandbox allows about 1 message per second per number."""

    MIN_GAP = 1.1

    def __init__(self, settings: Settings) -> None:
        self.s = settings
        self._lock = asyncio.Lock()
        self._last = 0.0

    async def send(self, wa_id: str, text: str) -> None:
        async with self._lock:
            wait = self.MIN_GAP - (time.monotonic() - self._last)
            if wait > 0:
                await asyncio.sleep(wait)
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.s.twilio_account_sid}/Messages.json"
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.post(
                    url,
                    auth=(self.s.twilio_account_sid, self.s.twilio_auth_token),
                    data={
                        "From": self.s.twilio_wa_from,
                        "To": f"whatsapp:+{wa_id}",
                        "Body": text[:1500],
                    },
                )
            self._last = time.monotonic()
            if r.status_code >= 400:
                raise RuntimeError(f"twilio send failed: {r.status_code} {r.text[:160]}")


def twilio_signature(auth_token: str, url: str, params: dict[str, str]) -> str:
    """X-Twilio-Signature: base64(HMAC-SHA1(token, url + sorted key+value pairs))."""
    data = url + "".join(k + params[k] for k in sorted(params))
    digest = hmac.new(auth_token.encode(), data.encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


def valid_signature(auth_token: str, url: str, params: dict[str, str], header: str | None) -> bool:
    return bool(header) and hmac.compare_digest(
        twilio_signature(auth_token, url, params), header or ""
    )


def normalise(params: dict[str, str]) -> Inbound:
    """Twilio form fields to our inbound shape (fixtures in specs/fixtures/wa_*.json)."""
    wa_id = params.get("From", "").removeprefix("whatsapp:").lstrip("+")
    media_type = params.get("MediaContentType0", "")
    if int(params.get("NumMedia", "0") or 0) > 0:
        kind = (
            "audio"
            if media_type.startswith("audio")
            else "image"
            if media_type.startswith("image")
            else "other"
        )
    else:
        kind = "text"
    return Inbound(
        wa_id=wa_id,
        type=kind,
        text=params.get("Body", ""),
        name=params.get("ProfileName") or None,
        media_url=params.get("MediaUrl0") or None,
        message_id=params.get("MessageSid"),
    )


def make_sender(settings: Settings) -> WaSender:
    if settings.wa_provider == "twilio_sandbox":
        return TwilioSandboxSender(settings)
    return LogSender()
