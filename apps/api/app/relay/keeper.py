"""The "please hold" keeper timer.

The keeper line is spoken only while the user is typing: after `after` seconds of continuous
typing (typing events keep arriving, gaps under `stale`), and at most once every `every` seconds
(20 s: repeating it every few seconds annoyed people on real calls).
Pure logic with an injectable clock; the session (or dev bridge) polls `due()`.
"""

import time
from collections.abc import Callable

AFTER = 5.0
EVERY = 20.0
STALE = 4.0


class Keeper:
    def __init__(
        self,
        after: float = AFTER,
        every: float = EVERY,
        stale: float = STALE,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.after, self.every, self.stale, self.clock = after, every, stale, clock
        self.since: float | None = None
        self.last_typing: float | None = None
        self.last_spoken = float("-inf")

    def typing(self) -> None:
        """A typing event; a gap longer than `stale` starts a new stretch of typing."""
        now = self.clock()
        if self.last_typing is None or now - self.last_typing > self.stale:
            self.since = now
        self.last_typing = now

    def reset(self) -> None:
        """The user sent something (or cancelled): typing is over."""
        self.since = None
        self.last_typing = None

    def due(self) -> bool:
        now = self.clock()
        return (
            self.since is not None
            and self.last_typing is not None
            and now - self.last_typing <= self.stale
            and now - self.since >= self.after
            and now - self.last_spoken >= self.every
        )

    def mark_spoken(self) -> None:
        self.last_spoken = self.clock()
