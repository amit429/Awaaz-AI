"""Twilio voice: answer URL (starts a bidirectional Media Stream) and the media WebSocket.

M0 spike: the media socket echoes the caller's audio back. The relay session replaces the echo later.
"""

import json
import logging
from xml.sax.saxutils import quoteattr

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)

from app.config import Settings, get_settings

log = logging.getLogger("awaaz.twilio")
router = APIRouter(prefix="/v1/twilio", tags=["twilio"])


def twiml_stream(ws_url: str, leg_id: str) -> str:
    """TwiML that connects the call to a bidirectional Media Stream (mu-law 8 kHz)."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response><Connect>"
        f"<Stream url={quoteattr(ws_url)}>"
        f'<Parameter name="leg_id" value={quoteattr(leg_id)}/>'
        "</Stream></Connect></Response>"
    )


def ws_base(settings: Settings) -> str:
    return settings.public_base_url.replace("https://", "wss://").replace("http://", "ws://")


def check_secret(s: str | None, settings: Settings) -> None:
    if s != settings.webhook_secret:
        raise HTTPException(status_code=403, detail="bad secret")


@router.api_route("/answer/{leg_id}", methods=["GET", "POST"])
async def answer(
    leg_id: str,
    request: Request,
    s: str | None = Query(None),
    settings: Settings = Depends(get_settings),
) -> Response:
    check_secret(s, settings)
    url = f"{ws_base(settings)}/v1/twilio/media/{leg_id}?s={settings.webhook_secret}"
    return Response(twiml_stream(url, leg_id), media_type="text/xml")


@router.websocket("/media/{leg_id}")
async def media(ws: WebSocket, leg_id: str, s: str | None = Query(None)) -> None:
    settings = get_settings()
    if s != settings.webhook_secret:
        await ws.close(code=4403)
        return
    await ws.accept()
    stream_sid: str | None = None
    frames = 0
    try:
        while True:
            msg = json.loads(await ws.receive_text())
            event = msg.get("event")
            if event == "start":
                stream_sid = msg["start"]["streamSid"]
                log.info("stream start leg=%s format=%s", leg_id, msg["start"].get("mediaFormat"))
            elif event == "media" and stream_sid:
                frames += 1
                await ws.send_text(
                    json.dumps(
                        {
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {"payload": msg["media"]["payload"]},
                        }
                    )
                )
            elif event == "stop":
                log.info("stream stop leg=%s frames=%d", leg_id, frames)
                break
    except WebSocketDisconnect:
        log.info("media socket closed leg=%s", leg_id)
