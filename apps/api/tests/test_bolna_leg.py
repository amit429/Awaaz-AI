import asyncio

import jwt
import pytest

import app.store as store_module
from app.config import get_settings
from app.main import app
from app.providers.bolna import BolnaError
from app.relay import bolna_registry, registry
from app.relay.bolna_leg import BolnaLeg
from app.relay.session import as_is
from app.store import InMemoryStore


class FakeBolna:
    def __init__(self, fail: str | None = None):
        self.fail, self.started, self.stopped = fail, [], []

    async def start_call(self, agent_id, to, user_data):
        if self.fail:
            raise BolnaError(self.fail)
        self.started.append((agent_id, to, user_data))
        return "exec-1"

    async def stop_call(self, execution_id):
        self.stopped.append(execution_id)


def make_leg(**kw) -> BolnaLeg:
    return BolnaLeg(
        FakeBolna(),
        agent_id="a1",
        to="+919876543210",
        call_id="call-1",
        disclosure="Namaste",
        settle=0.1,
        max_wait=1.0,
        tick=0.02,
        **kw,
    )


class Heard:
    def __init__(self):
        self.events: list[tuple[str, bool]] = []
        self.hung: list[str] = []

    async def heard(self, text, final):
        self.events.append((text, final))

    async def hangup(self, reason):
        self.hung.append(reason)


async def collect(leg, turn, heard):
    return [p async for p in leg.on_request(turn, heard)]


async def started_leg():
    leg, h = make_leg(), Heard()
    await leg.start(h.heard, h.hangup)
    return leg, h


async def test_start_places_call_with_call_id_and_disclosure():
    leg, _ = await started_leg()
    assert leg.client.started == [
        ("a1", "+919876543210", {"call_id": "call-1", "disclosure": "Namaste"})
    ]
    assert leg.execution_id == "exec-1" and leg.active


async def test_fragments_become_partials_then_one_final_after_settle():
    leg, h = await started_leg()
    task = asyncio.create_task(collect(leg, 1, "हाँ जी"))
    await asyncio.sleep(0.03)
    task2 = asyncio.create_task(collect(leg, 1, "हाँ जी। शर्मा मेडिकल।"))  # newer fragment
    await asyncio.sleep(0.35)  # settle passes
    assert await task == []  # superseded: silent
    finals = [e for e in h.events if e[1]]
    assert finals == [("हाँ जी। शर्मा मेडिकल।", True)]
    await leg.speak("Namaste")
    assert await task2 == ["Namaste"]


async def test_reply_goes_to_newest_request_and_finalises_the_caption_first():
    leg, h = await started_leg()
    task = asyncio.create_task(collect(leg, 1, "Telma 40 hai"))
    await asyncio.sleep(0.02)
    await leg.speak("Theek hai")  # typed before the settle timer fired
    assert await task == ["Theek hai"]
    assert ("Telma 40 hai", True) in h.events


async def test_keeper_line_then_reply_in_one_response():
    leg, _ = await started_leg()
    task = asyncio.create_task(collect(leg, 1, "kuch"))
    await asyncio.sleep(0.02)
    await leg.speak("Ek minute", final=False)
    await leg.speak("Haan ji", final=True)
    assert await task == ["Ek minute", "Haan ji"]


async def test_reply_typed_before_next_request_is_held():
    leg, _ = await started_leg()
    await leg.speak("Pehle se")
    assert await collect(leg, 2, "naya") == ["Pehle se"]


async def test_terminal_status_hangs_up_once():
    leg, h = await started_leg()
    await leg.on_status("in-progress")
    await leg.on_status("call-disconnected")
    await leg.on_status("completed")
    assert h.hung == ["callee_hung_up"]


async def test_hangup_stops_the_call():
    leg, _ = await started_leg()
    await leg.hangup()
    assert leg.client.stopped == ["exec-1"] and not leg.active


def test_registry_routes_by_token_and_falls_back_to_the_only_active_leg():
    bolna_registry.clear()
    a, b = make_leg(), make_leg()
    b.call_id = "call-2"
    a.active = b.active = True
    bolna_registry.add(a)
    bolna_registry.add(b)
    sys = lambda cid: [{"role": "system", "content": f"relay [[awaaz:call={cid}]]"}]
    assert bolna_registry.for_messages(sys("call-2")) is b
    assert (
        bolna_registry.for_messages([{"role": "system", "content": "no token"}]) is None
    )  # ambiguous
    bolna_registry.remove("call-2")
    assert bolna_registry.for_messages([{"role": "system", "content": "no token"}]) is a
    bolna_registry.clear()


# ---------- through the HTTP layer ----------
SECRET = "t" * 40


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)
    monkeypatch.setenv("MOCK_PROVIDERS", "false")
    monkeypatch.setenv("BOLNA_API_KEY", "k")
    monkeypatch.setenv("BOLNA_RELAY_AGENT_ID", "agent-1")
    get_settings.cache_clear()
    monkeypatch.setattr(store_module, "_store", InMemoryStore())
    registry.clear()
    bolna_registry.clear()
    yield
    registry.clear()
    bolna_registry.clear()
    get_settings.cache_clear()


def _token():
    return jwt.encode({"sub": "u1", "aud": "authenticated"}, SECRET, algorithm="HS256")


def async_client():
    import httpx

    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def _drain_until(q, pred, timeout=2.0):
    seen = []
    while True:
        ev = await asyncio.wait_for(q.get(), timeout)
        seen.append(ev)
        if pred(ev):
            return seen


async def test_live_call_flow_captions_reply_and_hangup(env, monkeypatch):
    fake = FakeBolna()
    monkeypatch.setattr("app.routers.calls.BolnaClient", lambda settings: fake)
    secret = get_settings().webhook_secret
    async with async_client() as ac:
        r = await ac.post(
            "/v1/calls",
            json={"to": "+919876543210"},
            headers={"Authorization": f"Bearer {_token()}"},
        )
        assert r.status_code == 200, r.text
        call_id = r.json()["session_id"]
        session = registry.get(call_id)
        session.prepare = as_is  # no real conversion calls in tests
        q = session.subscribe()
        await session.start()
        assert fake.started[0][2]["call_id"] == call_id
        await _drain_until(q, lambda e: e["t"] == "you.final" and e["source"] == "disclosure")

        # Bolna reports what the callee said; we answer with the text the user typed
        body = {
            "messages": [
                {"role": "system", "content": f"[[awaaz:call={call_id}]]"},
                {"role": "user", "content": "हाँ जी"},
            ]
        }
        post = asyncio.create_task(
            ac.post(
                "/v1/llm/chat/completions", json=body, headers={"Authorization": f"Bearer {secret}"}
            )
        )
        await asyncio.sleep(0.1)
        await session.handle({"t": "user.say", "text": "Namaste", "source": "typed"})
        r = await post
        assert "Namaste" in r.text and r.text.strip().endswith("[DONE]")
        seen = await _drain_until(q, lambda e: e["t"] == "caption.final")
        assert seen[-1]["text"] == "हाँ जी"

        # Bolna says the call is over
        r = await ac.post(
            f"/v1/webhooks/bolna?s={secret}", json={"id": "exec-1", "status": "call-disconnected"}
        )
        assert r.status_code == 200
        seen = await _drain_until(q, lambda e: e["t"] == "call.state" and e["state"] == "ended")
        assert seen[-1]["reason"] == "callee_hung_up"
        assert registry.get(call_id) is None  # cleaned up


async def test_live_call_failure_is_reported_to_the_user(env, monkeypatch):
    message = "Trial accounts can only make calls to verified phone numbers."
    monkeypatch.setattr("app.routers.calls.BolnaClient", lambda settings: FakeBolna(fail=message))
    async with async_client() as ac:
        r = await ac.post(
            "/v1/calls",
            json={"to": "+919876543210"},
            headers={"Authorization": f"Bearer {_token()}"},
        )
        session = registry.get(r.json()["session_id"])
        q = session.subscribe()
        await session.start()
        seen = await _drain_until(q, lambda e: e["t"] == "call.state" and e["state"] == "failed")
        assert seen[-1]["reason"] == message


async def test_webhook_requires_secret(env):
    async with async_client() as ac:
        r = await ac.post("/v1/webhooks/bolna?s=nope", json={})
    assert r.status_code == 403
