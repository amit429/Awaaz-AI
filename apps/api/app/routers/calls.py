"""POST /v1/calls (create a relay session) and WS /v1/relay/{id} (the app's live channel)."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.auth import _user_id, current_user
from app.config import Settings, get_settings
from app.relay import registry
from app.services.calls import CallError, create_relay_call
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
    try:
        session = await create_relay_call(
            user_id=user_id,
            to=body.to,
            settings=settings,
            store=store,
            call_language=body.call_language,
            talk_modes=body.talk_modes,
            hear_modes=body.hear_modes,
            callee=body.callee,
        )
    except CallError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc
    return {"session_id": session.call_id, "ws_url": ws_url(settings, session.call_id)}


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
        while not pump_task.done():
            receive = asyncio.create_task(ws.receive_text())
            await asyncio.wait({receive, pump_task}, return_when=asyncio.FIRST_COMPLETED)
            if not receive.done():  # the call ended and the pump closed the socket
                receive.cancel()
                break
            await session.handle_text(receive.result())
    except WebSocketDisconnect:
        pass
    finally:
        pump_task.cancel()
        session.unsubscribe(queue)
