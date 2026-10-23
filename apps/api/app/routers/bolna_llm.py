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
from app.providers import sarvam
from app.relay.dev_bridge import bridge

log = logging.getLogger("awaaz.bolna_llm")
router = APIRouter(tags=["bolna-llm"])

MODEL = "awaaz-relay"


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


def _text(content: object) -> str:
    if isinstance(content, str):
        return content
    return " ".join(p.get("text", "") for p in content or [] if isinstance(p, dict))


def current_turn(messages: list[dict]) -> tuple[int, str]:
    """(turn number, merged text of the other person's trailing messages).

    The turn number is how many assistant messages precede the trailing user block, so all
    fragments of one utterance share a turn.
    """
    tail: list[str] = []
    for m in reversed(messages):
        if m.get("role") == "user":
            tail.append(_text(m.get("content")).strip())
        elif m.get("role") == "assistant":
            break
    assistants = sum(1 for m in messages if m.get("role") == "assistant")
    return assistants, " ".join(reversed([t for t in tail if t]))


@router.get("/v1/llm/models", dependencies=[Depends(require_bearer)])
async def models() -> dict:
    return {"object": "list", "data": [{"id": MODEL, "object": "model", "owned_by": "awaaz"}]}


@router.post("/v1/llm/chat/completions", dependencies=[Depends(require_bearer)])
async def chat(request: Request) -> StreamingResponse:
    body = await request.json()
    turn, heard = current_turn(body.get("messages", []))
    if heard:
        bridge.hear(turn, heard)
        log.info("CAPTION turn=%d: %s", turn, heard)

    async def stream() -> AsyncIterator[str]:
        async for piece in bridge.respond():
            yield sse_chunk(piece + " ")
        yield sse_chunk(None, finish=True)
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.post("/v1/dev/say", dependencies=[Depends(require_bearer)])
async def dev_say(payload: dict) -> dict:
    bridge.say(str(payload["text"]))
    return {"queued": True}


@router.post("/v1/dev/preview", dependencies=[Depends(require_bearer)])
async def dev_preview(payload: dict, settings: Settings = Depends(get_settings)) -> dict:
    """Show-before-speak: romanised input and its native-script version."""
    original = str(payload["text"]).strip()
    hindi = await sarvam.transliterate(original, settings)
    return {"original": original, "hindi": hindi}


@router.post("/v1/dev/typing", dependencies=[Depends(require_bearer)])
async def dev_typing() -> dict:
    bridge.typing()
    return {"ok": True}


@router.get("/v1/dev/captions", dependencies=[Depends(require_bearer)])
async def dev_captions() -> dict:
    return {"captions": bridge.captions}
