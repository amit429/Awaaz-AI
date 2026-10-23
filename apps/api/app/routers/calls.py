"""POST /v1/calls (create a relay session) and WS /v1/relay/{id} (the app's live channel)."""

import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.auth import _user_id, current_user
from app.config import Settings, get_settings
from app.providers.bolna import BolnaClient
from app.providers.gemini import GeminiLlm
from app.providers.mocks import FakeCallee
from app.relay import bolna_registry, registry
from app.relay.bolna_leg import BolnaLeg
from app.relay.disclosure import disclosure_line
from app.relay.legs import MockLeg
from app.relay.session import RelaySession
from app.services.profiles import resolve_modes
from app.services.say_prep import make_preparer
from app.store import Store, get_store

router = APIRouter(tags=["calls"])


class CallRequest(BaseModel):
    to: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
    contact_id: str | None = None
    call_language: str | None = None
    talk_modes: list[str] | None = None
    hear_modes: list[str] | None = None
    callee: str | None = None  # fixture name; mock mode only


def ws_url(settings: Settings, call_id: str) -> str:
    base = settings.public_base_url.replace("https://", "wss://").replace("http://", "ws://")
    return f"{base}/v1/relay/{call_id}"


@router.post("/v1/calls")
async def create_call(
    body: CallRequest,
    user_id: str = Depends(current_user),
    settings: Settings = Depends(get_settings),
    store: Store = Depends(get_store),
) -> dict[str, str]:
    use_mock = bool(settings.mock_providers or body.callee)
    if not use_mock and not (settings.bolna_api_key and settings.bolna_relay_agent_id):
        raise HTTPException(status_code=501, detail="live telephony is not configured")
    profile = await store.get_profile(user_id)
    modes = resolve_modes(
        request_talk=body.talk_modes,
        request_hear=body.hear_modes,
        profile_talk=profile.talk_modes,
        profile_hear=profile.hear_modes,
        preset=profile.preset,
    )
    call_lang = body.call_language or "hi-IN"
    call_id = str(uuid.uuid4())
    await store.create_call(
        {
            "id": call_id,
            "user_id": user_id,
            "kind": "relay",
            "direction": "outbound",
            "other_number": body.to,
            "call_lang": call_lang,
            "talk_modes": modes.talk,
            "hear_modes": modes.hear,
            "status": "created",
            "provider": "mock" if use_mock else "bolna",
        }
    )
    if use_mock:
        try:
            leg = MockLeg(FakeCallee.from_fixture(body.callee or "pharmacy"))
        except FileNotFoundError as exc:
            raise HTTPException(status_code=422, detail="unknown callee fixture") from exc
        bolna_leg = None
    else:
        bolna_leg = BolnaLeg(
            BolnaClient(settings),
            agent_id=settings.bolna_relay_agent_id,
            to=body.to,
            call_id=call_id,
            disclosure=disclosure_line(profile.preset, call_lang, profile.display_name),
        )
        bolna_registry.add(bolna_leg)
        leg = bolna_leg

    def cleanup() -> None:
        registry.remove(call_id)
        bolna_registry.remove(call_id)

    registry.add(
        RelaySession(
            call_id=call_id,
            user_id=user_id,
            store=store,
            name=profile.display_name,
            preset=profile.preset,
            call_lang=call_lang,
            modes=modes,
            leg=leg,
            max_seconds=settings.max_call_minutes * 60,
            prepare=make_preparer(settings, call_lang, GeminiLlm(settings)),
            on_end=cleanup,
        )
    )
    return {"session_id": call_id, "ws_url": ws_url(settings, call_id)}


@router.get("/v1/calls/{call_id}")
async def get_call(
    call_id: str, user_id: str = Depends(current_user), store: Store = Depends(get_store)
) -> dict:
    call = await store.get_call(call_id)
    if not call or call["user_id"] != user_id:
        raise HTTPException(status_code=404)
    return {"call": call, "turns": await store.get_turns(call_id)}


@router.websocket("/v1/relay/{session_id}")
async def relay(
    ws: WebSocket,
    session_id: str,
    token: str | None = Query(None),
    last_turn: int = Query(0),
) -> None:
    try:
        user_id = _user_id(token, get_settings())
    except HTTPException:
        await ws.close(code=4401)
        return
    session = registry.get(session_id)
    if session is None or session.user_id != user_id:
        await ws.close(code=4404)
        return
    await ws.accept()
    queue = session.subscribe(last_turn)
    await session.start()

    async def pump() -> None:
        while True:
            event = await queue.get()
            await ws.send_json(event)
            if event.get("t") == "call.state" and event.get("state") == "ended":
                await ws.close()
                return

    pump_task = asyncio.create_task(pump())
    try:
        while True:
            await session.handle_text(await ws.receive_text())
    except WebSocketDisconnect:
        pass
    finally:
        pump_task.cancel()
        session.unsubscribe(queue)
