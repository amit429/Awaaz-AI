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
MAX_WAIT = 60.0
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
        self._final_sent: set[int] = set()
        self._settle_task: asyncio.Task[None] | None = None

    # ---------- OtherLeg ----------
    async def start(self, on_heard: HeardCallback, on_hangup: HangupCallback) -> None:
        self._on_heard, self._on_hangup = on_heard, on_hangup
        self.execution_id = await self.client.start_call(
            self.agent_id, self.to, {"call_id": self.call_id, "disclosure": self.disclosure}
        )
        self.active = True

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
        """One Bolna request = the callee spoke (maybe a fragment). Yields what to say back."""
        self._generation += 1
        mine = self._generation
        if heard:
            self._turn_text[turn] = heard
            if self._on_heard:
                await self._on_heard(heard, False)
            self._restart_settle(turn)
        deadline = time.monotonic() + self.max_wait
        while time.monotonic() < deadline:
            if self._generation != mine:
                return  # a newer fragment owns the reply
            try:
                text, final = await asyncio.wait_for(self._replies.get(), self.tick)
            except TimeoutError:
                continue
            if self._generation != mine:
                self._replies.put_nowait((text, final))
                return
            await self._finalize(turn)  # the user replied: the caption must be final by now
            yield text
            if final:
                return

    # ---------- internals ----------
    def _restart_settle(self, turn: int) -> None:
        if self._settle_task:
            self._settle_task.cancel()
        self._settle_task = asyncio.create_task(self._settle_then_final(turn))

    async def _settle_then_final(self, turn: int) -> None:
        await asyncio.sleep(self.settle)
        await self._finalize(turn)

    async def _finalize(self, turn: int) -> None:
        text = self._turn_text.get(turn)
        if text and turn not in self._final_sent and self._on_heard:
            self._final_sent.add(turn)
            await self._on_heard(text, True)
