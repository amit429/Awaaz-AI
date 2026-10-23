"""WhatsApp (Twilio sandbox) inbound webhook, plus dev-only endpoints to drive the bot without
WhatsApp (wa_provider=log)."""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from app.config import Settings, get_settings
from app.providers import twilio_wa
from app.providers.twilio_wa import Inbound, LogSender, make_sender
from app.services.wa_bot import WaBot, get_bot
from app.store import Store, get_store

log = logging.getLogger("awaaz.wa_webhook")
router = APIRouter(tags=["whatsapp"])
_tasks: set[asyncio.Task[None]] = set()
_sender = None


def sender_for(settings: Settings):
    global _sender
    if _sender is None:
        _sender = make_sender(settings)
    return _sender


def reset_sender() -> None:
    global _sender
    _sender = None


def bot_for(settings: Settings, store: Store) -> WaBot:
    return get_bot(settings, store, sender_for(settings))


@router.post("/v1/webhooks/wa/twilio_sandbox")
async def twilio_inbound(
    request: Request,
    s: str | None = Query(None),
    settings: Settings = Depends(get_settings),
    store: Store = Depends(get_store),
) -> Response:
    if s != settings.webhook_secret:
        raise HTTPException(status_code=403, detail="bad secret")
    form = await request.form()
    params = {k: str(v) for k, v in form.items()}
    if settings.twilio_auth_token:
        url = f"{settings.public_base_url.rstrip('/')}{request.url.path}"
        if request.url.query:
            url += f"?{request.url.query}"
        if not twilio_wa.valid_signature(
            settings.twilio_auth_token, url, params, request.headers.get("X-Twilio-Signature")
        ):
            raise HTTPException(status_code=403, detail="bad signature")
    msg = twilio_wa.normalise(params)
    task = asyncio.create_task(bot_for(settings, store).handle(msg))  # answer Twilio right away
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return Response("<Response></Response>", media_type="text/xml")


def _dev_only(settings: Settings) -> LogSender:
    if settings.app_env != "local" or settings.wa_provider != "log":
        raise HTTPException(status_code=404)
    sender = sender_for(settings)
    assert isinstance(sender, LogSender)
    return sender


@router.post("/v1/dev/wa")
async def dev_wa(
    payload: dict, settings: Settings = Depends(get_settings), store: Store = Depends(get_store)
) -> dict:
    """Pretend a WhatsApp message arrived: {"wa_id": "919800000001", "text": "...", "name": "Amit"}."""
    _dev_only(settings)
    await bot_for(settings, store).handle(
        Inbound(
            wa_id=str(payload.get("wa_id", "919800000001")),
            type="text",
            text=str(payload.get("text", "")),
            name=payload.get("name"),
        )
    )
    return {"ok": True}


@router.get("/v1/dev/wa/outbox")
async def dev_wa_outbox(
    wa_id: str | None = None, settings: Settings = Depends(get_settings)
) -> dict:
    return {"messages": _dev_only(settings).texts(wa_id)}
