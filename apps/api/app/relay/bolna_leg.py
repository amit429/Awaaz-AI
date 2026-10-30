"""BolnaLeg: a real phone call through a Bolna agent whose "LLM" is our server.

Bolna transcribes the callee and calls POST /v1/llm/chat/completions with the conversation; we
turn those requests into caption events and hold the response open until the user has typed
something to say (see docs/SPIKE-bolna.md for why: fragments, one waiter, no unrequested speech).
"""

import asyncio
import contextlib
import time
from collections import deque
from collections.abc import AsyncIterator
from typing import Protocol

from app.relay.legs import HangupCallback, HeardCallback

SETTLE = 1.2  # seconds without new fragments before a turn counts as finished
MAX_WAIT = 60.0  # an open request is kept this long waiting for the user to send something
BATCH = 0.3  # after the first message, wait this long for others sent right behind it
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
        batch: float = BATCH,
    ) -> None:
        self.client, self.agent_id, self.to = client, agent_id, to
        self.call_id, self.disclosure = call_id, disclosure
        self.settle, self.max_wait, self.tick, self.batch = settle, max_wait, tick, batch
        self.execution_id: str | None = None
        self.active = False
        self._on_heard: HeardCallback | None = None
        self._on_hangup: HangupCallback | None = None
        self._replies: deque[tuple[str, bool]] = deque()  # (text, final) waiting to be spoken
        self._ready = asyncio.Event()  # set while _replies is not empty
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

    @property
    def can_hold_line(self) -> bool:
        """Bolna voices a response only once it is complete, and drops it if the other person
        speaks first, so a "please wait" line can never be heard while the user is still typing."""
        return False

    async def speak(self, text: str, *, final: bool = True) -> None:
        self._replies.append((text, final))
        self._ready.set()

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

        Bolna voices a response only when it is complete, so the request is held open only until
        the user sends something, then answered and closed at once (messages sent right behind
        each other go out together). A held-open request left typed messages unspoken until the
        other person talked again, and they were dropped if the call ended first. A message sent
        after the request closed waits for the next one.
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
                batch = self._take()
                if not batch:
                    with contextlib.suppress(TimeoutError):
                        await asyncio.wait_for(self._ready.wait(), self.tick)
                    continue
                if not any(final for _, final in batch):
                    continue  # only a hold line: it cannot be heard in time, see can_hold_line
                await self._finalize(turn)  # the user replied: the caption must be final by now
                await asyncio.sleep(self.batch)  # catch messages sent right behind this one
                batch += self._take()
                if self._generation != mine or not self.active:
                    self._give_back(batch)
                    return
                for text, final in batch:
                    if final:
                        yield end_sentence(text)
                return
        finally:
            self._open -= 1

    # ---------- internals ----------
    def _take(self) -> list[tuple[str, bool]]:
        items = list(self._replies)
        self._replies.clear()
        self._ready.clear()
        return items

    def _give_back(self, items: list[tuple[str, bool]]) -> None:
        """Return taken messages to the front of the queue, in their original order."""
        self._replies.extendleft(reversed(items))
        if self._replies:
            self._ready.set()

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
