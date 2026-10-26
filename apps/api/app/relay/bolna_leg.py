"""BolnaLeg: a real phone call through a Bolna agent whose "LLM" is our server.

Bolna transcribes the callee and calls POST /v1/llm/chat/completions with the conversation; we
turn those requests into caption events and hold the response open until the user has typed
something to say (see docs/SPIKE-bolna.md for why: fragments, one waiter, no unrequested speech).
"""

import asyncio
import contextlib
import time
from collections.abc import AsyncIterator
from typing import Protocol

from app.relay.legs import HangupCallback, HeardCallback

SETTLE = 1.2  # seconds without new fragments before a turn counts as finished
MAX_WAIT = 60.0  # an open request is kept this long after the last thing said on it
ENDS = ".!?।॥"
TICK = 0.3

TERMINAL = {
    "call-disconnected",
    "completed",
    "failed",
    "error",
    "no-answer",
    "busy",
    "canceled",
    "stopped",
}


class CallStarter(Protocol):
    async def start_call(self, agent_id: str, to: str, user_data: dict) -> str: ...
    async def stop_call(self, execution_id: str) -> None: ...


class BolnaLeg:
    def __init__(
        self,
        client: CallStarter,
        *,
        agent_id: str,
        to: str,
        call_id: str,
        disclosure: str,
        settle: float = SETTLE,
        max_wait: float = MAX_WAIT,
        tick: float = TICK,
    ) -> None:
        self.client, self.agent_id, self.to = client, agent_id, to
        self.call_id, self.disclosure = call_id, disclosure
        self.settle, self.max_wait, self.tick = settle, max_wait, tick
        self.execution_id: str | None = None
        self.active = False
        self._on_heard: HeardCallback | None = None
        self._on_hangup: HangupCallback | None = None
        self._replies: asyncio.Queue[tuple[str, bool]] = asyncio.Queue()
        self._generation = 0
        self._turn_text: dict[int, str] = {}
        self._final_text: dict[int, str] = {}  # what of each turn is already shown as final
        self._open = 0  # requests from Bolna currently waiting for something to say
        self._settle_task: asyncio.Task[None] | None = None

    # ---------- OtherLeg ----------
    async def start(self, on_heard: HeardCallback, on_hangup: HangupCallback) -> None:
        self._on_heard, self._on_hangup = on_heard, on_hangup
        self.execution_id = await self.client.start_call(
            self.agent_id, self.to, {"call_id": self.call_id, "disclosure": self.disclosure}
        )
        self.active = True

    @property
    def listening(self) -> bool:
        """True while Bolna is waiting on us, so anything said now is spoken at once. Otherwise it
        waits until the other person speaks again (Bolna only asks after they speak)."""
        return self._open > 0

    async def speak(self, text: str, *, final: bool = True) -> None:
        self._replies.put_nowait((text, final))

    async def hangup(self) -> None:
        self.active = False
        if self._settle_task:
            self._settle_task.cancel()
        if self.execution_id:
            with contextlib.suppress(Exception):
                await self.client.stop_call(self.execution_id)

    # ---------- driven by Bolna ----------
    async def on_status(self, status: str) -> None:
        if status in TERMINAL and self.active and self._on_hangup:
            self.active = False
            await self._on_hangup("callee_hung_up" if status == "call-disconnected" else status)

    async def on_request(self, turn: int, heard: str) -> AsyncIterator[str]:
        """One Bolna request = the callee spoke (maybe a fragment). Yields what to say back.

        The request stays open after a reply, so the user can send several messages in a row and
        each is spoken at once. It closes when the callee speaks again (a newer request takes
        over) or after `max_wait` seconds with nothing to say.
        """
        self._generation += 1
        mine = self._generation
        if heard:
            self._turn_text[turn] = heard
            unsaid = self._unsaid(turn, heard)
            if unsaid and self._on_heard:
                await self._on_heard(unsaid, False)
            self._restart_settle(turn)
        self._open += 1
        try:
            deadline = time.monotonic() + self.max_wait
            while time.monotonic() < deadline:
                if self._generation != mine or not self.active:
                    return  # a newer fragment owns the reply, or the call is over
                try:
                    text, _final = await asyncio.wait_for(self._replies.get(), self.tick)
                except TimeoutError:
                    continue
                if self._generation != mine:
                    self._replies.put_nowait((text, _final))
                    return
                await self._finalize(turn)  # the user replied: the caption must be final by now
                yield end_sentence(text)
                deadline = time.monotonic() + self.max_wait  # stay open for the next message
        finally:
            self._open -= 1

    # ---------- internals ----------
    def _restart_settle(self, turn: int) -> None:
        if self._settle_task:
            self._settle_task.cancel()
        self._settle_task = asyncio.create_task(self._settle_then_final(turn))

    async def _settle_then_final(self, turn: int) -> None:
        await asyncio.sleep(self.settle)
        await self._finalize(turn)

    def _unsaid(self, turn: int, text: str) -> str:
        """The part of this turn not yet shown as final (Bolna resends earlier fragments)."""
        done = self._final_text.get(turn, "")
        if done and text.startswith(done):
            return text[len(done) :].strip()
        return text if text != done else ""

    async def _finalize(self, turn: int) -> None:
        text = self._turn_text.get(turn)
        if not text or not self._on_heard:
            return
        unsaid = self._unsaid(turn, text)
        if not unsaid:
            return
        self._final_text[turn] = text
        await self._on_heard(unsaid, True)


def end_sentence(text: str) -> str:
    """Bolna speaks text as it streams in, sentence by sentence: a reply without a full stop could
    wait for more text. Make sure each one ends a sentence."""
    t = text.rstrip()
    if not t or t[-1] in ENDS:
        return t + " "
    devanagari = any("\u0900" <= ch <= "\u097f" for ch in t)
    return t + ("। " if devanagari else ". ")
