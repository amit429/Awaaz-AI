"""Spike bridge for the Bolna-as-phone-line path (single active call, dev only).

Bolna sends the other person's words to our fake "LLM" endpoint; we record them as captions
and wait for the user's typed reply, which Bolna speaks. Replaced by RelaySession later.
"""

import asyncio
from dataclasses import dataclass, field


@dataclass
class DevBridge:
    captions: list[str] = field(default_factory=list)
    replies: asyncio.Queue[str] = field(default_factory=asyncio.Queue)

    def caption(self, text: str) -> None:
        self.captions.append(text)

    async def next_reply(self, timeout: float) -> str | None:
        try:
            return await asyncio.wait_for(self.replies.get(), timeout)
        except TimeoutError:
            return None


bridge = DevBridge()
