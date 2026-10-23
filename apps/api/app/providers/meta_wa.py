"""WhatsApp Cloud API (Meta): sending, webhook verification, signature check, payload parsing.

Free-form text can be sent within 24 hours of the user's last message; the test number needs the
recipient added and verified in the Meta dashboard.
"""

import asyncio
import hashlib
import hmac
import time
from typing import Any

import httpx

from app.config import Settings
from app.providers.twilio_wa import Inbound


def graph_url(settings: Settings, path: str) -> str:
    version = f"/{settings.meta_graph_version.strip('/')}" if settings.meta_graph_version else ""
    return f"https://graph.facebook.com{version}/{path}"


class MetaSender:
    MIN_GAP = 0.3  # stay well under Meta's per-recipient pacing

    def __init__(self, settings: Settings) -> None:
        self.s = settings
        self._lock = asyncio.Lock()
        self._last = 0.0

    async def send(self, wa_id: str, text: str) -> None:
        body = {
            "messaging_product": "whatsapp",
            "to": wa_id,
            "type": "text",
            "text": {"body": text[:4000], "preview_url": False},
        }
        async with self._lock:
            wait = self.MIN_GAP - (time.monotonic() - self._last)
            if wait > 0:
                await asyncio.sleep(wait)
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.post(
                    graph_url(self.s, f"{self.s.meta_wa_phone_id}/messages"),
                    json=body,
                    headers={"Authorization": f"Bearer {self.s.meta_wa_token}"},
                )
            self._last = time.monotonic()
        if r.status_code >= 400:
            raise RuntimeError(f"meta send failed: {r.status_code} {r.text[:200]}")


def valid_signature(app_secret: str, raw_body: bytes, header: str | None) -> bool:
    """X-Hub-Signature-256: 'sha256=' + HMAC-SHA256(app secret, raw body)."""
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


def parse_webhook(payload: dict[str, Any]) -> list[Inbound]:
    """Messages in a Cloud API webhook (status updates and other events are skipped)."""
    out: list[Inbound] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            names = {
                c.get("wa_id"): (c.get("profile") or {}).get("name")
                for c in value.get("contacts", [])
            }
            for m in value.get("messages", []):
                wa_id = str(m.get("from", ""))
                kind = m.get("type", "other")
                if kind == "text":
                    out.append(
                        Inbound(
                            wa_id, "text", m["text"]["body"], names.get(wa_id), None, m.get("id")
                        )
                    )
                elif kind == "audio":
                    out.append(
                        Inbound(
                            wa_id,
                            "audio",
                            "",
                            names.get(wa_id),
                            (m.get("audio") or {}).get("id"),
                            m.get("id"),
                        )
                    )
                elif kind == "interactive":
                    reply = (m.get("interactive") or {}).get("button_reply") or {}
                    out.append(
                        Inbound(
                            wa_id,
                            "text",
                            reply.get("title", ""),
                            names.get(wa_id),
                            None,
                            m.get("id"),
                        )
                    )
                else:
                    out.append(Inbound(wa_id, "other", "", names.get(wa_id), None, m.get("id")))
    return out
