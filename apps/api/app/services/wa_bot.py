"""WhatsApp bot. Idle: start a call ("call 98765 43210", "call practice pharmacy"). On a call:
captions arrive as messages (numbers in bold), whatever the user types is spoken, with the same
conversion and confirmation rules as the app. Commands: end, again, hold, ok / cancel."""

import asyncio
import contextlib
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from app.config import Settings
from app.providers.twilio_wa import Inbound, WaSender
from app.relay.entities import extract_entities
from app.relay.session import RelaySession
from app.services.calls import CallError, create_relay_call
from app.store import Store

log = logging.getLogger("awaaz.wa")

HELP = (
    "Hi, I’m Awaaz. I make phone calls possible for people who can’t hear or speak.\n\n"
    "Send *call 98765 43210* to start a call. I’ll show what they say here, and anything you "
    "type is spoken to them.\n\n"
    "During a call:\n*again* asks them to repeat\n*hold* asks them to wait while you type\n"
    "*end* hangs up"
)
IN_CALL_HELP = "On a call: type what you want to say. *again* asks them to repeat, *hold* asks them to wait, *end* hangs up."
PRACTICE = {"pharmacy": "pharmacy", "clinic": "clinic_mr", "bank": "bank_scam"}
END_WORDS = {"end", "hang up", "hangup", "cut", "stop call", "band", "khatam", "end call"}
AGAIN_WORDS = {"again", "repeat", "phir se", "dobara", "ask again"}
HOLD_WORDS = {"hold", "wait", "ruko", "ek minute"}
YES_WORDS = {"ok", "okay", "yes", "y", "haan", "ha", "send", "theek hai", "👍"}
NO_WORDS = {"no", "cancel", "nahi"}
END_REASONS = {
    "callee_hung_up": "They hung up.",
    "user": "You ended the call.",
    "max_call_minutes": "The call reached the time limit.",
    "app_disconnected": "The call ended because the app disconnected.",
}
NUMBER = re.compile(r"(?<![\d])(\+?\d[\d\s\-]{8,16}\d)(?![\d])")


def mask(number: str) -> str:
    return f"••••{number[-4:]}"


def to_e164(raw: str) -> str | None:
    digits = re.sub(r"[^\d+]", "", raw)
    if digits.startswith("+") and 9 <= len(digits) <= 16:
        return digits
    digits = digits.lstrip("+")
    if len(digits) == 10 and digits[0] in "6789":
        return f"+91{digits}"
    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    return None


def bold_entities(text: str) -> str:
    """WhatsApp bold (*...*) around numbers, prices, times and dates."""
    out, at = [], 0
    for e in extract_entities(text):
        out.append(text[at : e.start])
        out.append(f"*{text[e.start : e.end]}*")
        at = e.end
    out.append(text[at:])
    return "".join(out)


@dataclass
class WaCall:
    wa_id: str
    session: RelaySession
    number: str
    queue: asyncio.Queue[dict[str, Any]] = field(default_factory=asyncio.Queue)
    pending_preview: str | None = None
    task: asyncio.Task[None] | None = None
    active: bool = True


class WaBot:
    def __init__(self, settings: Settings, store: Store, sender: WaSender) -> None:
        self.settings, self.store, self.sender = settings, store, sender
        self.calls: dict[str, WaCall] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def say(self, wa_id: str, text: str) -> None:
        try:
            await self.sender.send(wa_id, text)
        except Exception:
            log.exception("whatsapp send failed")

    async def handle(self, msg: Inbound) -> None:
        lock = self._locks.setdefault(msg.wa_id, asyncio.Lock())
        async with lock:  # keep one user's messages in order
            user_id = await self.store.wa_user(msg.wa_id, msg.name)
            if msg.type != "text":
                return await self.say(
                    msg.wa_id, "I can read text for now. Voice notes are coming soon."
                )
            text = msg.text.strip()
            if not text:
                return
            call = self.calls.get(msg.wa_id)
            if call and call.active:
                await self._in_call(call, text)
            else:
                await self._idle(msg.wa_id, user_id, text)

    # ---------- idle ----------
    async def _idle(self, wa_id: str, user_id: str, text: str) -> None:
        low = text.lower()
        practice = re.search(r"practice\s+(pharmacy|clinic|bank)", low)
        number = NUMBER.search(text)
        if practice:
            kind = practice.group(1)
            return await self._start(wa_id, user_id, "+919800000000", callee=PRACTICE[kind])
        if number and re.search(r"\b(call|phone|dial|ring|baat)\b|call", low):
            e164 = to_e164(number.group(1))
            if e164:
                return await self._start(wa_id, user_id, e164)
            return await self.say(wa_id, "I couldn’t read that number. Try: *call 98765 43210*")
        await self.say(wa_id, HELP)

    async def _start(
        self, wa_id: str, user_id: str, number: str, callee: str | None = None
    ) -> None:
        try:
            session = await create_relay_call(
                user_id=user_id,
                to=number,
                settings=self.settings,
                store=self.store,
                callee=callee,
                source="whatsapp",
            )
        except CallError as exc:
            return await self.say(wa_id, f"I couldn’t start that call: {exc.detail}")
        call = WaCall(wa_id=wa_id, session=session, number=number)
        call.queue = session.subscribe()
        self.calls[wa_id] = call
        call.task = asyncio.create_task(self._pump(call))
        await self.say(
            wa_id,
            f"Calling {mask(number) if not callee else 'a practice caller'}. I’ll show what they say. "
            "Type to reply. *again* asks them to repeat, *hold* asks them to wait, *end* hangs up.",
        )
        await session.start()

    # ---------- on a call ----------
    async def _in_call(self, call: WaCall, text: str) -> None:
        low = text.lower().strip().rstrip(".!")
        s = call.session
        if low in END_WORDS:
            return await s.handle({"t": "call.end"})
        if low in AGAIN_WORDS:
            return await s.handle({"t": "user.ask_repeat"})
        if low in HOLD_WORDS:
            return await s.hold()
        if low in {"help", "?"}:
            return await self.say(call.wa_id, IN_CALL_HELP)
        if call.pending_preview:
            preview_id, call.pending_preview = call.pending_preview, None
            if low in YES_WORDS:
                return await s.handle({"t": "say.confirm", "preview_id": preview_id})
            if low in NO_WORDS:
                return await self.say(call.wa_id, "Okay, not sent.")
        await s.handle({"t": "user.say", "text": text, "source": "typed"})

    async def _pump(self, call: WaCall) -> None:
        """Session events to WhatsApp messages."""
        try:
            while call.active:
                ev = await call.queue.get()
                text = self._render(call, ev)
                if text:
                    await self.say(call.wa_id, text)
                if ev["t"] == "call.state" and ev["state"] in ("ended", "failed"):
                    break
        finally:
            call.active = False
            call.session.unsubscribe(call.queue)
            self.calls.pop(call.wa_id, None)

    def _render(self, call: WaCall, ev: dict[str, Any]) -> str | None:
        t = ev["t"]
        if t == "call.state":
            if ev["state"] == "ended":
                return "Call ended. " + END_REASONS.get(ev.get("reason") or "", "")
            if ev["state"] == "failed":
                return f"The call didn’t connect: {ev.get('reason') or 'unknown error'}"
            return None
        if t == "caption.final":
            line = f"*Them:* {bold_entities(ev['text'])}"
            return line + (f"\n_{ev['translated']}_" if ev.get("translated") else "")
        if t == "you.final":
            if ev["source"] in ("disclosure", "keeper", "ask_repeat"):
                return f"Awaaz told them: “{ev['text']}”"
            if ev.get("original"):
                return f"Said: “{ev['text']}”"
            return None
        if t == "say.preview":
            call.pending_preview = ev["preview_id"]
            return f"Say this? “{ev['text']}”\nReply *ok* to send, *cancel* to drop it, or type something else."
        if t == "say.blocked":
            return {
                "scam_digits": "Not sent: I won’t speak OTP or PIN digits on this call.",
                "empty": "Nothing to send.",
                "too_long": "That message is too long. Please shorten it.",
            }.get(ev["reason"], "Not sent.")
        if t == "scam.warning":
            return "Warning: they asked for an OTP or PIN. Don’t share it."
        if t == "error":
            return ev.get("message")
        return None

    async def shutdown(self) -> None:
        for call in list(self.calls.values()):
            call.active = False
            if call.task:
                call.task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await call.task


_bot: WaBot | None = None


def get_bot(settings: Settings, store: Store, sender: WaSender) -> WaBot:
    global _bot
    if _bot is None:
        _bot = WaBot(settings, store, sender)
    return _bot


def reset_bot() -> None:
    global _bot
    _bot = None
