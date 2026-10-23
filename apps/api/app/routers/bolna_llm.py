"""OpenAI-compatible endpoint that Bolna calls as a "custom LLM" (spike).

base_url registered in Bolna = {PUBLIC_BASE_URL}/v1/llm. Auth: Authorization: Bearer <WEBHOOK_SECRET>.
"""

import json
import logging
import time
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.config import Settings, get_settings
from app.relay.dev_bridge import bridge

log = logging.getLogger("awaaz.bolna_llm")
router = APIRouter(tags=["bolna-llm"])

MODEL = "awaaz-relay"
KEEPER_LINE = "Ek minute, please hold."
WAIT_SECONDS = 12.0


def require_bearer(
    authorization: str | None = Header(None), settings: Settings = Depends(get_settings)
) -> None:
    if authorization != f"Bearer {settings.webhook_secret}":
        raise HTTPException(status_code=401, detail="bad key")


def sse_chunk(text: str | None, *, finish: bool = False) -> str:
    delta = {"role": "assistant", "content": text} if text is not None else {}
    body = {
        "id": "chatcmpl-awaaz",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": MODEL,
        "choices": [{"index": 0, "delta": delta, "finish_reason": "stop" if finish else None}],
    }
    return f"data: {json.dumps(body, ensure_ascii=False)}\n\n"


def last_user_text(messages: list[dict]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            c = m.get("content")
            return c if isinstance(c, str) else " ".join(p.get("text", "") for p in c or [])
    return ""


@router.get("/v1/llm/models", dependencies=[Depends(require_bearer)])
async def models() -> dict:
    return {"object": "list", "data": [{"id": MODEL, "object": "model", "owned_by": "awaaz"}]}


@router.post("/v1/llm/chat/completions", dependencies=[Depends(require_bearer)])
async def chat(request: Request) -> StreamingResponse:
    body = await request.json()
    heard = last_user_text(body.get("messages", []))
    if heard:
        bridge.caption(heard)
        log.info("CAPTION: %s", heard)

    async def stream() -> AsyncIterator[str]:
        reply = await bridge.next_reply(WAIT_SECONDS)
        yield sse_chunk(reply or KEEPER_LINE)
        yield sse_chunk(None, finish=True)
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.post("/v1/dev/say", dependencies=[Depends(require_bearer)])
async def dev_say(payload: dict) -> dict:
    await bridge.replies.put(str(payload["text"]))
    return {"queued": True}


@router.get("/v1/dev/captions", dependencies=[Depends(require_bearer)])
async def dev_captions() -> dict:
    return {"captions": bridge.captions}
