import httpx
import pytest

import app.store as store_module
from app.auth import current_user
from app.config import get_settings
from app.main import app
from app.relay import registry


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("MOCK_PROVIDERS", "true")
    monkeypatch.setenv("DAILY_MINUTES_PER_USER", "1")
    get_settings.cache_clear()
    registry.clear()
    app.dependency_overrides[current_user] = lambda: "u1"
    yield httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")
    app.dependency_overrides.clear()
    registry.clear()
    get_settings.cache_clear()


async def test_one_call_at_a_time(client):
    async with client as ac:
        assert (await ac.post("/v1/calls", json={"to": "+919876543210"})).status_code == 200
        second = await ac.post("/v1/calls", json={"to": "+919876543211"})
        assert second.status_code == 409 and "already have a call" in second.json()["detail"]
        session = next(iter(registry._sessions.values()))
        await session.end("user")
        assert (await ac.post("/v1/calls", json={"to": "+919876543211"})).status_code == 200


async def test_daily_minutes_limit(client):
    store = store_module.get_store()
    async with client as ac:
        await store.create_call({"id": "old", "user_id": "u1", "kind": "relay"})
        await store.update_call("old", duration_s=61)  # one minute allowed, 61 s used
        r = await ac.post("/v1/calls", json={"to": "+919876543210"})
        assert r.status_code == 429 and "limit" in r.json()["detail"]
        await store.create_call({"id": "other", "user_id": "u2", "kind": "relay"})
        await store.update_call("other", duration_s=9999)  # another user's minutes do not count
    app.dependency_overrides[current_user] = lambda: "u3"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as ac:
        assert (await ac.post("/v1/calls", json={"to": "+919876543210"})).status_code == 200


async def test_ended_call_records_duration():
    from app.providers.mocks import FakeCallee
    from app.relay.legs import MockLeg
    from app.relay.session import RelaySession
    from app.services.profiles import Modes

    store = store_module.get_store()
    await store.create_call({"id": "c9", "user_id": "u9", "kind": "relay"})
    s = RelaySession(
        call_id="c9",
        user_id="u9",
        store=store,
        name="R",
        preset=None,
        call_lang="hi-IN",
        modes=Modes(["type"], ["captions"]),
        leg=MockLeg(FakeCallee.from_fixture("pharmacy")),
    )
    await s.start()
    await s.end("user")
    call = await store.get_call("c9")
    assert call["status"] == "ended" and call["duration_s"] >= 0 and call["ended_at"]


async def test_in_memory_store_ends_orphaned_calls_but_leaves_finished_ones():
    from app.store import InMemoryStore

    store = InMemoryStore()
    for call_id, status in (("a", "created"), ("b", "ringing"), ("c", "connected"), ("d", "ended")):
        await store.create_call({"id": call_id, "user_id": "u", "status": status})
    assert await store.end_orphaned_calls() == 3
    assert {c: (await store.get_call(c))["status"] for c in "abcd"} == dict.fromkeys("abcd", "ended")
