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
from app.providers.gemini import GeminiLlm
from app.relay.dev_bridge import bridge
from app.services.say_prep import prepare_say

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
        async for piece in bridge.respond(turn):
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


@router.post("/v1/dev/prepare", dependencies=[Depends(require_bearer)])
async def dev_prepare(payload: dict, settings: Settings = Depends(get_settings)) -> dict:
    """What would be spoken for this typed text, and whether it needs a confirmation."""
    p = await prepare_say(str(payload["text"]), "hi-IN", settings, GeminiLlm(settings))
    return {
        "spoken": p.spoken,
        "needs_confirm": p.needs_confirm,
        "kind": p.kind,
        "detected": p.detected,
    }


@router.post("/v1/dev/autoreply", dependencies=[Depends(require_bearer)])
async def dev_autoreply(payload: dict, settings: Settings = Depends(get_settings)) -> dict:
    """Scripted test mode: reply automatically (in order) to each turn. Texts are prepared first."""
    texts = [str(t).strip() for t in payload.get("replies", []) if str(t).strip()]
    llm = GeminiLlm(settings)
    prepared = [await prepare_say(t, "hi-IN", settings, llm) for t in texts]
    bridge.auto_replies = [p.spoken for p in prepared]
    bridge._auto_turn = None
    return {"loaded": len(bridge.auto_replies), "first": bridge.auto_replies[:2]}


@router.post("/v1/dev/reset", dependencies=[Depends(require_bearer)])
async def dev_reset() -> dict:
    bridge.captions.clear()
    bridge.events.clear()
    bridge.auto_replies = []
    bridge._auto_turn = None
    bridge.keeper.reset()
    return {"reset": True}


@router.post("/v1/dev/typing", dependencies=[Depends(require_bearer)])
async def dev_typing() -> dict:
    bridge.typing()
    return {"ok": True}


_read_cache: dict[tuple[str, str], str] = {}


@router.get("/v1/dev/log", dependencies=[Depends(require_bearer)])
async def dev_log() -> dict:
    return {"events": bridge.events, "captions": bridge.captions}


@router.get("/v1/dev/captions", dependencies=[Depends(require_bearer)])
async def dev_captions(mode: str = "original", settings: Settings = Depends(get_settings)) -> dict:
    """Captions with a `read` field in the chosen reading mode (original text always included)."""
    if mode not in sarvam.READ_MODES:
        raise HTTPException(status_code=400, detail="bad mode")
    out = []
    for c in list(bridge.captions):
        key = (c["text"], mode)
        if key not in _read_cache:
            try:
                _read_cache[key] = await sarvam.for_reading(c["text"], mode, settings)
            except Exception:  # provider hiccup: fall back to the original rather than hide it
                log.exception("caption conversion failed")
                _read_cache[key] = c["text"]
        out.append({**c, "read": _read_cache[key]})
    return {"captions": out, "mode": mode}
