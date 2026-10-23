"""The other person's side of a call. A leg delivers what they say and speaks what the user sends.

Implementations: MockLeg (scripted fake callee), BolnaLeg (phone call through a Bolna agent),
and later the browser callee simulator.
"""

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from typing import Protocol

from app.providers.mocks import FakeCallee

HeardCallback = Callable[[str, bool], Awaitable[None]]  # text, final
HangupCallback = Callable[[str], Awaitable[None]]  # reason


class OtherLeg(Protocol):
    async def start(self, on_heard: HeardCallback, on_hangup: HangupCallback) -> None: ...

    async def speak(self, text: str, *, final: bool = True) -> None:
        """Say `text` to the other person. final=False means more speech will follow (keeper line)."""

    async def hangup(self) -> None: ...


class MockLeg:
    """Plays a scripted callee (specs/fixtures/callee_*.json): text in, text out."""

    def __init__(self, callee: FakeCallee, reply_delay: float = 0.05) -> None:
        self.callee = callee
        self.reply_delay = reply_delay
        self._on_heard: HeardCallback | None = None
        self._tasks: set[asyncio.Task[None]] = set()

    async def start(self, on_heard: HeardCallback, on_hangup: HangupCallback) -> None:
        self._on_heard = on_heard
        self._spawn(self._reply(None))

    async def speak(self, text: str, *, final: bool = True) -> None:
        if final:  # the keeper line does not advance the script
            self._spawn(self._reply(text))

    async def hangup(self) -> None:
        for t in list(self._tasks):
            t.cancel()

    def _spawn(self, coro: Awaitable[None]) -> None:
        task = asyncio.ensure_future(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _reply(self, user_text: str | None) -> None:
        await asyncio.sleep(self.reply_delay)
        line = self.callee.opening() if user_text is None else self.callee.reply_to(user_text)
        if line and self._on_heard:
            with contextlib.suppress(asyncio.CancelledError):
                await self._on_heard(line["text"], True)
