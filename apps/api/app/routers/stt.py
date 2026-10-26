"""Live speech to text for the user's own voice: the browser streams microphone audio here, we
stream it to Sarvam (Saaras) and send back what was said. The key stays on the server.

Browser to us: binary frames of 16 kHz, 16-bit mono PCM.
Us to browser: {"t": "vad", "signal": "start" | "end"} and {"t": "transcript", "text": ...}.
"""

import asyncio
import base64
import contextlib
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


RECONNECTS = 5  # Sarvam sometimes drops a long stream (seen: close 1011); reopen it this often


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
    audio: asyncio.Queue[bytes] = asyncio.Queue(maxsize=200)
    client_gone = asyncio.Event()

    async def from_app() -> None:
        """Microphone audio from the app, kept in a queue so a Sarvam reconnect loses nothing."""
        try:
            while time.monotonic() < deadline:
                pcm = await ws.receive_bytes()
                if audio.full():
                    audio.get_nowait()  # never let a stalled upstream build up a backlog
                audio.put_nowait(pcm)
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            client_gone.set()

    async def one_stream() -> None:
        """One Sarvam connection; returns (or raises) when Sarvam closes it."""
        async with websockets.connect(
            sarvam_url(language),
            additional_headers={"api-subscription-key": settings.sarvam_api_key},
        ) as upstream:

            async def up() -> None:
                while True:
                    await upstream.send(audio_message(await audio.get()))

            async def down() -> None:
                async for raw in upstream:
                    event = to_client(json.loads(raw))
                    if event:
                        await ws.send_json(event)

            tasks = [asyncio.create_task(up()), asyncio.create_task(down())]
            gone = asyncio.create_task(client_gone.wait())
            try:
                await asyncio.wait([*tasks, gone], return_when=asyncio.FIRST_COMPLETED)
            finally:
                for t in [*tasks, gone]:
                    t.cancel()
                await asyncio.gather(*tasks, gone, return_exceptions=True)

    reader = asyncio.create_task(from_app())
    failures = 0
    try:
        while not client_gone.is_set() and time.monotonic() < deadline:
            started = time.monotonic()
            try:
                await one_stream()
            except Exception as exc:  # noqa: BLE001 - Sarvam dropped the stream: reopen it
                log.warning("live speech to text stream closed (%s); reconnecting", exc)
            if client_gone.is_set():
                break
            # A stream that ran a while was fine; only quick repeated failures count.
            failures = failures + 1 if time.monotonic() - started < 5 else 1
            if failures > RECONNECTS:
                await ws.send_json({"t": "error", "code": "stt_failed"})
                break
            await asyncio.sleep(min(0.25 * failures, 2))
    finally:
        reader.cancel()
        await asyncio.gather(reader, return_exceptions=True)
        with contextlib.suppress(Exception):
            await ws.close()
