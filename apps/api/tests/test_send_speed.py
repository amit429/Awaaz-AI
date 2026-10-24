"""Sending must feel instant: text is prepared while the user types, and a slow message never
holds up other events."""

import asyncio
import json
import time

from app.relay.legs import MockLeg
from app.relay.session import Modes, RelaySession
from app.services.say_prep import Prepared
from app.store import InMemoryStore
from tests.test_languages import FakeCallee


def _prepare(delay, calls):
    async def prepare(text):
        calls.append(text)
        await asyncio.sleep(delay)
        return Prepared(f"<{text}>", False, "same_language")

    return prepare


async def _session(prepare):
    store = InMemoryStore()
    await store.create_call({"id": "c1", "user_id": "u1"})
    s = RelaySession(
        call_id="c1",
        user_id="u1",
        store=store,
        name="R",
        preset="mute",
        call_lang="hi-IN",
        modes=Modes(["type"], ["captions"]),
        leg=MockLeg(FakeCallee.from_fixture("pharmacy"), reply_delay=0.01),
        prepare=prepare,
    )
    q = s.subscribe()
    await s.start()
    return s, q


async def _until(q, kind, source=None, limit=40):
    for _ in range(limit):
        e = await asyncio.wait_for(q.get(), 3)
        if e["t"] == kind and (source is None or e.get("source") == source):
            return e
    raise AssertionError(kind)


async def test_text_prepared_while_typing_is_sent_instantly():
    calls = []
    s, q = await _session(_prepare(0.4, calls))
    s.dispatch_text(json.dumps({"t": "say.prefetch", "text": "Telma 40 chahiye"}))
    await asyncio.sleep(0.6)  # the user keeps typing; preparation finishes meanwhile
    t0 = time.monotonic()
    s.dispatch_text(json.dumps({"t": "user.say", "text": "Telma 40 chahiye", "source": "typed"}))
    e = await _until(q, "you.final", "typed")
    assert e["text"] == "<Telma 40 chahiye>"
    assert time.monotonic() - t0 < 0.2
    assert calls == ["Telma 40 chahiye"]  # prepared once, not again on send


async def test_a_slow_message_does_not_block_other_events_and_order_is_kept():
    s, q = await _session(_prepare(0.3, []))
    s.dispatch_text(json.dumps({"t": "user.say", "text": "pehla", "source": "typed"}))
    s.dispatch_text(json.dumps({"t": "user.say", "text": "doosra", "source": "typed"}))
    t0 = time.monotonic()
    s.dispatch_text(json.dumps({"t": "ping"}))
    await _until(q, "ping")
    assert time.monotonic() - t0 < 0.15  # not queued behind the slow messages
    first = await _until(q, "you.final", "typed")
    second = await _until(q, "you.final", "typed")
    assert [first["text"], second["text"]] == ["<pehla>", "<doosra>"]
