"""Live speech to text for the user's own voice: the browser streams microphone audio here, we
stream it to Sarvam (Saaras) and send back what was said. The key stays on the server.

Browser to us: binary frames of 16 kHz, 16-bit mono PCM.
Us to browser: {"t": "vad", "signal": "start" | "end"} and {"t": "transcript", "text": ...}.
"""

import asyncio
import base64
import json
import logging
import time
from typing import Any
from urllib.parse import urlencode

import websockets
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

from app.auth import _user_id
from app.config import get_settings
from app.services.languages import SPOKEN

log = logging.getLogger("awaaz.stt")
router = APIRouter(tags=["stt"])

SARVAM_WS = "wss://api.sarvam.ai/speech-to-text/ws"
SAMPLE_RATE = 16000


def to_client(message: dict[str, Any]) -> dict[str, Any] | None:
    """A Sarvam message as the small event the app understands; None for anything else."""
    kind = message.get("type")
    data = message.get("data") or {}
    if kind == "events":
        signal = {"START_SPEECH": "start", "END_SPEECH": "end"}.get(data.get("signal_type"))
        return {"t": "vad", "signal": signal} if signal else None
    if kind == "data":
        text = str(data.get("transcript", "")).strip()
        return {"t": "transcript", "text": text} if text else None
    return None


def audio_message(pcm: bytes) -> str:
    """Sarvam wants the audio inside an object; raw PCM goes with input_audio_codec=pcm_s16le."""
    data = {
        "data": base64.b64encode(pcm).decode(),
        "encoding": "audio/wav",
        "sample_rate": SAMPLE_RATE,
    }
    return json.dumps({"audio": data})


def sarvam_url(language: str) -> str:
    """The key goes in a header (the query-parameter form in the docs is rejected)."""
    query = {
        "model": "saaras:v3",
        "mode": "transcribe",
        "language_code": language,
        "sample_rate": SAMPLE_RATE,
        "input_audio_codec": "pcm_s16le",
        "high_vad_sensitivity": "true",
        "vad_signals": "true",
    }
    return f"{SARVAM_WS}?{urlencode(query)}"


@router.websocket("/v1/stt/ws")
async def stt(ws: WebSocket, token: str | None = Query(None), lang: str = Query("hi")) -> None:
    settings = get_settings()
    try:
        _user_id(token, settings)
    except HTTPException:
        await ws.close(code=4401)
        return
    await ws.accept()
    if settings.mock_providers or not settings.sarvam_api_key:
        await ws.send_json({"t": "error", "code": "stt_unavailable"})
        await ws.close()
        return
    language = SPOKEN.get(lang, SPOKEN["hi"])[1]
    deadline = time.monotonic() + settings.max_call_minutes * 60
    try:
        async with websockets.connect(
            sarvam_url(language),
            additional_headers={"api-subscription-key": settings.sarvam_api_key},
        ) as upstream:

            async def up() -> None:
                while time.monotonic() < deadline:
                    pcm = await ws.receive_bytes()
                    await upstream.send(audio_message(pcm))

            async def down() -> None:
                async for raw in upstream:
                    event = to_client(json.loads(raw))
                    if event:
                        await ws.send_json(event)

            tasks = [asyncio.create_task(up()), asyncio.create_task(down())]
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            log.debug(
                "stt tasks done: %s upstream=%s %s",
                [t.get_coro().__name__ for t in done],
                upstream.close_code,
                upstream.close_reason,
            )
            for t in done:
                if t.exception():
                    raise t.exception()
            for t in tasks:
                t.cancel()
    except (WebSocketDisconnect, websockets.ConnectionClosed) as exc:
        log.debug("live speech to text closed: %r", exc)
    except Exception:
        log.exception("live speech to text failed")
        try:
            await ws.send_json({"t": "error", "code": "stt_failed"})
        except Exception:  # noqa: BLE001
            pass
    try:
        await ws.close()
    except Exception:  # noqa: BLE001
        pass
