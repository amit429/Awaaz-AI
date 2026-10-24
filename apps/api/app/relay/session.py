"""RelaySession: one live call. Owns turn numbering, the routing of user actions to the other
person, captions back to the user, the keeper timer, and persistence of every final turn.

The other person's side is a `Callee` (scripted fake callee in mock mode; telephony legs later).
Events are plain dicts matching specs/protocol/relay-events.schema.json.
"""

import asyncio
import contextlib
import json
import logging
import re
import time
import uuid
from collections import deque
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError

from app.models.events import (
    AskRepeat,
    CallEnd,
    DraftRequest,
    ModeSet,
    Ping,
    SayConfirm,
    UserSay,
    UserTyping,
    client_event,
)
from app.providers.base import Llm
from app.relay import scam
from app.relay.disclosure import ask_repeat_line, disclosure_line, keeper_line, short_lang
from app.relay.entities import extract_entities
from app.relay.keeper import Keeper
from app.relay.legs import OtherLeg
from app.services.drafts import make_draft
from app.services.profiles import Modes
from app.services.replies import ReplyContext, suggest
from app.services.say_prep import Prepared
from app.store import Store

log = logging.getLogger("awaaz.relay")

DIGIT_RUN = re.compile(r"(?<!\d)\d{4,8}(?!\d)")
Preparer = Callable[[str], Awaitable[Prepared]]


async def as_is(text: str) -> Prepared:
    return Prepared(text, False, "as_is")


MAX_TEXT = 500
REPLAY = 20


class RelaySession:
    def __init__(
        self,
        *,
        call_id: str,
        user_id: str,
        store: Store,
        name: str,
        preset: str | None,
        call_lang: str,
        modes: Modes,
        leg: OtherLeg,
        keeper: Keeper | None = None,
        prepare: Preparer = as_is,
        on_end: Callable[[], None] | None = None,
        llm: Llm | None = None,
        reply_ctx: ReplyContext | None = None,
        max_seconds: float = 15 * 60,
        idle_seconds: float = 60.0,
    ) -> None:
        self.call_id, self.user_id, self.store = call_id, user_id, store
        self.name, self.preset, self.call_lang = name, preset, call_lang
        self.modes = modes
        self.leg = leg
        self.keeper = keeper or Keeper()
        self.prepare = prepare
        self.on_end = on_end
        self.llm = llm
        self.reply_ctx = reply_ctx or ReplyContext(user_name=name)
        self._convo: list[tuple[str, str]] = []  # (speaker, text) for suggestions
        self._reply_task: asyncio.Task[None] | None = None
        self._recent_other: list[str] = []
        self._pending: dict[str, tuple[str, str, str]] = {}  # preview_id -> (spoken, source, typed)
        self.max_seconds, self.idle_seconds = max_seconds, idle_seconds
        self.seq = 0
        self.scam = False  # set by the scam shield (M5); digit runs are blocked once true
        self.state = "created"
        self.started = False
        self.ended = False
        self._t0 = time.monotonic()
        self._started_wall = time.time()
        self._subs: list[asyncio.Queue[dict[str, Any]]] = []
        self._buffer: deque[dict[str, Any]] = deque(maxlen=REPLAY)
        self._tasks: set[asyncio.Task[None]] = set()
        self._last_sub_gone: float | None = None

    # ---------- events out ----------
    def elapsed_ms(self) -> int:
        return int((time.monotonic() - self._t0) * 1000)

    def emit(self, event: dict[str, Any]) -> None:
        if "turn" in event and event["t"] != "caption.partial":
            self._buffer.append(event)
        for q in self._subs:
            q.put_nowait(event)

    def subscribe(self, last_turn: int = 0) -> asyncio.Queue[dict[str, Any]]:
        """New listener. Replays buffered events newer than `last_turn` (reconnect recovery)."""
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        if self.started:
            q.put_nowait(self._state_event(self.state))
            for ev in self._buffer:
                if ev["turn"] > last_turn:
                    q.put_nowait(ev)
        self._subs.append(q)
        self._last_sub_gone = None
        return q

    def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        with contextlib.suppress(ValueError):
            self._subs.remove(q)
        if not self._subs:
            self._last_sub_gone = time.monotonic()

    def _state_event(self, state: str, reason: str | None = None) -> dict[str, Any]:
        ev: dict[str, Any] = {"t": "call.state", "state": state, "elapsed_ms": self.elapsed_ms()}
        if reason:
            ev["reason"] = reason
        return ev

    def _set_state(self, state: str, reason: str | None = None) -> None:
        self.state = state
        self.emit(self._state_event(state, reason))

    # ---------- turns ----------
    async def _turn(self, speaker: str, source: str, text: str, **extra: Any) -> int:
        self.seq += 1
        await self.store.add_turn(
            self.call_id,
            {
                "seq": self.seq,
                "speaker": speaker,
                "source": source,
                "text": text,
                "t_ms": self.elapsed_ms(),
                **extra,
            },
        )
        return self.seq

    async def _you(
        self, text: str, source: str, speaker: str = "user", original: str | None = None
    ) -> int:
        turn = await self._turn(speaker, source, text)
        event: dict[str, Any] = {"t": "you.final", "turn": turn, "text": text, "source": source}
        if original and original != text:
            event["original"] = original  # what the user typed, when it was converted
        self.emit(event)
        return turn

    async def _other_says(self, text: str, lang: str | None = None) -> int:
        entities = [e.as_dict() for e in extract_entities(text)]
        lang = lang or short_lang(self.call_lang)
        turn = await self._turn("other", "stt", text, lang=lang, confidence=0.95, entities=entities)
        self.emit(
            {
                "t": "caption.final",
                "turn": turn,
                "text": text,
                "lang": lang,
                "translated": None,
                "confidence": 0.95,
                "entities": entities,
            }
        )
        self._convo.append(("other", text))
        await self._scam_check(text, turn)
        self._schedule_suggestions(turn)
        return turn

    def _schedule_suggestions(self, turn: int) -> None:
        """Three one-tap replies for this turn; dropped if the user or the other person moves on."""
        if self._reply_task:
            self._reply_task.cancel()
        if not self.llm or "replies" not in self.modes.talk or self.ended:
            return
        llm = self.llm

        async def run() -> None:
            items = await suggest(llm, self.reply_ctx, self._convo)
            if items and self.seq == turn and not self.ended:  # nothing newer happened
                self.emit({"t": "suggestions", "turn": turn, "items": items})

        self._reply_task = asyncio.create_task(run())
        self._tasks.add(self._reply_task)
        self._reply_task.add_done_callback(self._tasks.discard)

    async def _scam_check(self, text: str, turn: int) -> None:
        """Warn when the other person asks for a code or a remote-access app; from then on digit
        runs are never spoken (see _user_say)."""
        self._recent_other.append(text)
        match = scam.check(text)
        if match is None:
            return
        confirmed = await scam.second_opinion(match, self._recent_other, self.llm)
        if confirmed is None:
            return
        self.scam = True
        self.emit({"t": "scam.warning", "reason": confirmed.reason, "turn": turn})
        await self.store.add_scam_event(self.call_id, turn, confirmed.reason, "warned")

    # ---------- lifecycle ----------
    async def start(self) -> None:
        """Dial and connect (mock: instantly), speak the disclosure, let the callee answer."""
        if self.started:
            return
        self.started = True
        await self.store.update_call(self.call_id, status="ringing")
        self._set_state("ringing")
        self._set_state("connected")
        await self.store.update_call(self.call_id, status="connected")
        line = disclosure_line(self.preset, self.call_lang, self.name)
        await self._you(line, "disclosure", speaker="system")
        self._spawn(self._watchdog())
        try:
            await self.leg.start(self._heard, self._leg_hangup)
        except Exception as exc:  # noqa: BLE001 - show the user why the call could not start
            log.warning("leg failed to start: %s", exc)
            await self.fail(getattr(exc, "message", None) or "Could not start the call")

    async def fail(self, reason: str) -> None:
        if self.ended:
            return
        self.ended = True
        for t in list(self._tasks):
            if t is not asyncio.current_task():
                t.cancel()
        self._set_state("failed", reason)
        await self.store.update_call(self.call_id, status="failed")
        if self.on_end:
            self.on_end()

    async def end(self, reason: str | None = None) -> None:
        if self.ended:
            return
        self.ended = True
        for t in list(self._tasks):
            if t is not asyncio.current_task():
                t.cancel()
        self._set_state("ended", reason)
        with contextlib.suppress(Exception):
            await self.leg.hangup()
        await self.store.update_call(
            self.call_id,
            status="ended",
            ended_at=datetime.now(UTC).isoformat(),
            duration_s=int(time.time() - self._started_wall) if self.started else 0,
        )
        if self.on_end:
            self.on_end()

    def _spawn(self, coro: Any) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _heard(self, text: str, final: bool) -> None:
        """The other person said something (partial transcripts update the live caption)."""
        if self.ended:
            return
        if final:
            await self._other_says(text)
        else:
            self.emit({"t": "caption.partial", "turn": self.seq + 1, "text": text})

    async def _leg_hangup(self, reason: str) -> None:
        await self.end(reason)

    async def hold(self) -> None:
        """Tell the other person the user is typing, please hold (also used by WhatsApp's "hold")."""
        if self.ended:
            return
        line = keeper_line(self.call_lang, self.name)
        await self._you(line, "keeper", speaker="system")
        self.emit({"t": "keeper.spoken"})
        await self.leg.speak(line, final=False)

    async def _watchdog(self) -> None:
        """Keeper line while the user types; cost guard (max call length); idle cleanup."""
        while not self.ended:
            await asyncio.sleep(0.25)
            if self.keeper.due():
                self.keeper.mark_spoken()
                await self.hold()
            if time.monotonic() - self._t0 > self.max_seconds:
                await self.end("max_call_minutes")
            elif (
                self._last_sub_gone is not None
                and time.monotonic() - self._last_sub_gone > self.idle_seconds
            ):
                await self.end("app_disconnected")

    # ---------- events in ----------
    def _error(self, code: str, message: str) -> None:
        self.emit({"t": "error", "code": code, "message": message})

    async def handle(self, raw: Any) -> None:
        if not isinstance(raw, dict):
            return self._error("bad_event", "event must be a JSON object")
        if raw.get("t") == "user.say":
            text = str(raw.get("text", ""))
            if not text.strip():
                return self.emit({"t": "say.blocked", "reason": "empty"})
            if len(text) > MAX_TEXT:
                return self.emit({"t": "say.blocked", "reason": "too_long"})
        try:
            ev = client_event.validate_python(raw)
        except ValidationError:
            return self._error("bad_event", f"invalid event: {raw.get('t')!r}")
        if self.ended:
            return self._error("call_ended", "the call has ended")
        match ev:
            case UserTyping():
                self.keeper.typing()
            case UserSay():
                await self._user_say(ev)
            case SayConfirm():
                await self._say_confirm(ev)
            case DraftRequest():
                await self._draft(ev)
            case AskRepeat():
                line = ask_repeat_line(self.call_lang)
                await self._you(line, "ask_repeat")
                await self.leg.speak(line)
            case ModeSet():
                if ev.talk_modes:
                    self.modes = Modes(list(ev.talk_modes), self.modes.hear)
                if ev.hear_modes:
                    self.modes = Modes(self.modes.talk, list(ev.hear_modes))
                self.emit(
                    {
                        "t": "mode.updated",
                        "talk_modes": self.modes.talk,
                        "hear_modes": self.modes.hear,
                    }
                )
            case CallEnd():
                await self.end("user")
            case Ping():
                self.emit({"t": "ping"})
            case _:
                self._error("not_implemented", f"{ev.t} is not available yet")

    async def _user_say(self, ev: UserSay) -> None:
        # Digit runs are checked on what the user typed: conversion may spell numbers out.
        if self.scam and DIGIT_RUN.search(ev.text):
            return self.emit({"t": "say.blocked", "reason": "scam_digits"})
        if ev.preview_id and ev.preview_id in self._pending:
            return await self._say_confirm(SayConfirm(t="say.confirm", preview_id=ev.preview_id))
        try:
            prepared = await self.prepare(ev.text)
        except Exception:
            log.exception("say preparation failed")
            prepared = Prepared(ev.text, True, "same_language")
        if prepared.needs_confirm:
            preview_id = uuid.uuid4().hex[:12]
            self._pending[preview_id] = (prepared.spoken, ev.source, ev.text)
            self.emit(
                {
                    "t": "say.preview",
                    "preview_id": preview_id,
                    "text": prepared.spoken,
                    "original": ev.text,
                }
            )
            return
        await self._speak(prepared.spoken, ev.source, ev.text)

    async def _draft(self, ev: DraftRequest) -> None:
        """Help me say it: draft one sentence from a few words. Nothing is spoken here."""
        if not self.llm:
            return self._error("not_available", "Help me say it needs the live AI service.")
        last = next((t for who, t in reversed(self._convo) if who == "other"), "")
        draft = await make_draft(
            self.llm,
            words=ev.words,
            call_lang=self.call_lang,
            type_lang=self.reply_ctx.type_lang,
            last_caption=last,
            contact_notes=self.reply_ctx.contact_notes,
        )
        if draft is None:
            return self._error("draft_failed", "I couldn’t draft that. Try different words.")
        draft_id = uuid.uuid4().hex[:12]
        self.emit(
            {
                "t": "draft.ready",
                "draft_id": draft_id,
                "text": draft.text,
                "from_words": ev.words,
                "changed_meaning_risk": draft.risk,
            }
        )

    async def _say_confirm(self, ev: SayConfirm) -> None:
        pending = self._pending.pop(ev.preview_id, None)
        if pending is None:
            return self._error("unknown_preview", "nothing to confirm")
        spoken, source, typed = pending
        await self._speak(spoken, source, typed)

    async def _speak(self, text: str, source: str, original: str | None = None) -> None:
        self.keeper.reset()
        if self._reply_task:
            self._reply_task.cancel()
        self._convo.append(("user", text))
        if source == "typed":
            self.reply_ctx.typed.append(original or text)
        await self._you(text, source, original=original)
        await self.leg.speak(text)

    async def handle_text(self, data: str) -> None:
        try:
            raw = json.loads(data)
        except json.JSONDecodeError:
            return self._error("bad_event", "not valid JSON")
        await self.handle(raw)
