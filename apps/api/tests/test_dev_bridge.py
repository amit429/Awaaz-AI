import asyncio

from app.relay.dev_bridge import KEEPER_LINE, DevBridge


def fast(**kw) -> DevBridge:
    return DevBridge(tick=0.02, max_wait=0.5, keeper_after=0.1, keeper_every=0.3, **kw)


async def collect(b: DevBridge) -> list[str]:
    return [p async for p in b.respond()]


async def test_reply_goes_to_waiting_request():
    b = fast()
    task = asyncio.create_task(collect(b))
    await asyncio.sleep(0.05)
    b.say("Theek hai")
    assert await task == ["Theek hai"]


async def test_older_request_is_superseded_and_stays_silent():
    b = fast()
    old = asyncio.create_task(collect(b))
    await asyncio.sleep(0.05)
    new = asyncio.create_task(collect(b))
    await asyncio.sleep(0.05)
    b.say("Haan ji")
    assert await old == []
    assert await new == ["Haan ji"]


async def test_reply_typed_before_any_request_is_held():
    b = fast()
    b.say("Pehle se likha")
    assert await collect(b) == ["Pehle se likha"]


async def test_timeout_speaks_nothing():
    assert await collect(fast()) == []


async def test_keeper_only_after_typing_and_not_repeated_too_fast():
    b = fast()
    b.typing()
    task = asyncio.create_task(collect(b))
    await asyncio.sleep(0.2)  # past keeper_after, before keeper_every elapses again
    b.say("Done")
    out = await task
    assert out == [KEEPER_LINE, "Done"]


async def test_no_keeper_without_typing():
    b = fast()
    task = asyncio.create_task(collect(b))
    await asyncio.sleep(0.3)
    b.say("Hello")
    assert await task == ["Hello"]


def test_fragments_of_one_turn_merge_into_one_caption():
    b = DevBridge()
    b.hear(1, "तेलमा चालीस मिल जाएगा।")
    b.hear(1, "तेलमा चालीस मिल जाएगा। चार सौ बीस।")
    b.hear(2, "ठीक है।")
    assert [c["text"] for c in b.captions] == ["तेलमा चालीस मिल जाएगा। चार सौ बीस।", "ठीक है।"]
