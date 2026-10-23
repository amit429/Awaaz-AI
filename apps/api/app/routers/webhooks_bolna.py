"""Bolna status webhook: ends the relay session when the phone call ends."""

import logging

from fastapi import APIRouter, Depends, Query, Request

from app.config import Settings, get_settings
from app.relay import bolna_registry
from app.routers.twilio_voice import check_secret

log = logging.getLogger("awaaz.bolna_webhook")
router = APIRouter(tags=["webhooks"])


@router.post("/v1/webhooks/bolna")
async def bolna_webhook(
    request: Request, s: str | None = Query(None), settings: Settings = Depends(get_settings)
) -> dict:
    check_secret(s, settings)
    payload = await request.json()
    execution_id = str(payload.get("id") or payload.get("execution_id") or "")
    status = str(payload.get("status") or "")
    log.info("bolna webhook: status=%s keys=%s", status, sorted(payload)[:12])
    leg = bolna_registry.for_execution(execution_id) if execution_id else None
    if leg:
        await leg.on_status(status)
    return {"ok": True}
