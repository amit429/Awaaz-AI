"""Spike bridge for the Bolna-as-phone-line path (single active call, dev only).

Bolna sends the other person's words to our fake "LLM" endpoint. One request is "the callee
finished a turn". Rules that keep the conversation clean:
- Only the newest request waits for the user's reply; older ones end silently (Bolna splits one
  sentence into several fragments, each opening a request).
- Fragments of one utterance are merged into one caption turn.
- The keeper line is spoken only after the user has been typing for KEEPER_AFTER seconds, and at
  most every KEEPER_EVERY seconds. A timeout never speaks.
- A reply typed while no request is waiting is held for the next one.
"""

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

KEEPER_LINE = "Ek minute, please hold."
KEEPER_AFTER = 5.0
KEEPER_EVERY = 8.0
MAX_WAIT = 60.0
TICK = 0.4


@dataclass
class DevBridge:
    captions: list[dict] = field(default_factory=list)  # turn, text, first_at, last_at, fragments
    events: list[dict] = field(default_factory=list)  # timing log: {"t", "type", ...}
    replies: asyncio.Queue[str] = field(default_factory=asyncio.Queue)
    generation: int = 0
    typing_since: float | None = None
    last_keeper: float = float("-inf")
    keeper_after: float = KEEPER_AFTER
    keeper_every: float = KEEPER_EVERY
    max_wait: float = MAX_WAIT
    auto_replies: list[str] = field(default_factory=list)  # scripted test replies, spoken in order
    auto_settle: float = 1.8  # wait for fragments to stop before replying
    _auto_turn: int | None = None
    tick: float = TICK

    def log(self, kind: str, **info: object) -> None:
        self.events.append({"t": time.time(), "type": kind, **info})

    def hear(self, turn: int, text: str) -> None:
        """Record what the other person said; fragments of the same turn replace each other."""
        now = time.time()
        if self.captions and self.captions[-1]["turn"] == turn:
            c = self.captions[-1]
            c.update(text=text, last_at=now, fragments=c["fragments"] + 1)
        else:
            self.captions.append(
                {"turn": turn, "text": text, "first_at": now, "last_at": now, "fragments": 1}
            )
        self.log("heard", turn=turn, text=text)

    def typing(self) -> None:
        if self.typing_since is None:
            self.typing_since = time.monotonic()

    def say(self, text: str) -> None:
        self.typing_since = None
        self.log("say", text=text)
        self.replies.put_nowait(text)

    def _keeper_due(self, now: float) -> bool:
        return (
            self.typing_since is not None
            and now - self.typing_since >= self.keeper_after
            and now - self.last_keeper >= self.keeper_every
        )

    async def respond(self, turn: int | None = None) -> AsyncIterator[str]:
        """Pieces of speech for one request; empty if superseded or nothing is said in time."""
        self.generation += 1
        mine = self.generation
        self.log("request", generation=mine)
        started = time.monotonic()
        deadline = started + self.max_wait
        while time.monotonic() < deadline:
            if self.generation != mine:
                self.log("superseded", generation=mine)
                return
            try:
                reply = await asyncio.wait_for(self.replies.get(), self.tick)
            except TimeoutError:
                now = time.monotonic()
                if (
                    self.auto_replies
                    and turn is not None
                    and turn != self._auto_turn
                    and now - started >= self.auto_settle
                ):
                    self._auto_turn = turn
                    text = self.auto_replies.pop(0)
                    self.log("spoken", text=text, auto=True)
                    yield text
                    return
                if self._keeper_due(now):
                    self.last_keeper = now
                    self.log("keeper")
                    yield KEEPER_LINE
                continue
            if self.generation != mine:
                self.replies.put_nowait(reply)  # a newer request owns the reply
                return
            self.log("spoken", text=reply)
            yield reply
            return
        self.log("timeout", generation=mine)


bridge = DevBridge()
