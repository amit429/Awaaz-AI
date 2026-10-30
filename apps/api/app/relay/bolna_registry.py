"""Active Bolna legs: find the leg for an incoming Bolna request or status webhook."""

import re

from app.relay.bolna_leg import BolnaLeg

_legs: dict[str, BolnaLeg] = {}  # call_id -> leg
TOKEN = re.compile(r"\[\[awaaz:call=([A-Za-z0-9-]+)\]\]")


def add(leg: BolnaLeg) -> None:
    _legs[leg.call_id] = leg
    leg.on_finished = lambda: remove(leg.call_id)


def remove(call_id: str) -> None:
    _legs.pop(call_id, None)


def release(call_id: str) -> None:
    """The session is over. Keep a leg that still owes the other person a goodbye: Bolna will
    ask for it the next time they speak (the leg removes itself once the call is over)."""
    leg = _legs.get(call_id)
    if leg is not None and leg.lingering:
        return
    _legs.pop(call_id, None)


def clear() -> None:
    _legs.clear()


def for_messages(messages: list[dict]) -> BolnaLeg | None:
    """The leg named by the call token in the system prompt; else the only active leg."""
    for m in messages:
        content = m.get("content")
        if m.get("role") == "system" and isinstance(content, str):
            hit = TOKEN.search(content)
            if hit and hit.group(1) in _legs:
                return _legs[hit.group(1)]
    active = [leg for leg in _legs.values() if leg.active]
    return active[0] if len(active) == 1 else None


def for_execution(execution_id: str) -> BolnaLeg | None:
    return next((leg for leg in _legs.values() if leg.execution_id == execution_id), None)
