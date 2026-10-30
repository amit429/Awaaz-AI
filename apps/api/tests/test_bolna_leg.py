import asyncio

import jwt
import pytest

import app.store as store_module
from app.config import get_settings
from app.main import app
from app.providers.bolna import BolnaError
from app.relay import bolna_registry, registry
from app.relay.bolna_leg import BolnaLeg, end_sentence
from app.relay.session import as_is
from app.store import InMemoryStore


class FakeBolna:
    def __init__(
        self, fail: str | None = None, refuse_stops: int = 0, live_status: str | None = None
    ):
        self.fail, self.started, self.stopped = fail, [], []
        self.refuse_stops = refuse_stops  # Bolna refuses this many stops ("not started yet")
        self.live_status = live_status  # a call in progress: Bolna refuses every stop

    async def start_call(self, agent_id, to, user_data):
        if self.fail:
            raise BolnaError(self.fail)
        self.started.append((agent_id, to, user_data))
        return "exec-1"

    async def stop_call(self, execution_id):
        self.stopped.append(execution_id)
        if self.live_status:
            return self.live_status
        if len(self.stopped) <= self.refuse_stops:
            return "initiated"
        return "stopped"


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
        batch=0.05,
        stop_retry=0.02,
        goodbye="Amit ne call khatam kiya. Namaste.",
        linger=0.5,
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
    assert await task2 == ["Namaste. "]


async def test_reply_goes_to_newest_request_and_finalises_the_caption_first():
    leg, h = await started_leg()
    task = asyncio.create_task(collect(leg, 1, "Telma 40 hai"))
    await asyncio.sleep(0.02)
    await leg.speak("Theek hai")  # typed before the settle timer fired
    assert await task == ["Theek hai. "]
    assert ("Telma 40 hai", True) in h.events


async def test_hold_line_is_not_voiced_ahead_of_the_reply():
    """Bolna voices a response only once it is complete, so a "please wait" line sent before the
    reply is heard glued to it (and not at all if the other person speaks first). Drop it."""
    leg, _ = await started_leg()
    task = asyncio.create_task(collect(leg, 1, "kuch"))
    await asyncio.sleep(0.02)
    await leg.speak("Ek minute", final=False)
    await leg.speak("Haan ji", final=True)
    assert await task == ["Haan ji. "]


async def test_hold_line_alone_is_never_spoken():
    leg, _ = await started_leg()
    task = asyncio.create_task(collect(leg, 1, "kuch"))
    await asyncio.sleep(0.02)
    await leg.speak("Ek minute", final=False)
    assert await task == []


async def test_reply_typed_before_next_request_is_held():
    leg, _ = await started_leg()
    await leg.speak("Pehle se")
    assert await collect(leg, 2, "naya") == ["Pehle se. "]


async def test_a_reply_closes_the_request_so_bolna_speaks_it_now():
    """Bolna only voices a response when it is complete: a request held open after the reply left
    the typed message unspoken (or lost) until the other person talked again."""
    leg, _ = await started_leg()
    task = asyncio.create_task(collect(leg, 1, "Boliye"))
    await asyncio.sleep(0.02)
    assert leg.listening
    await leg.speak("Pehli baat")
    assert await asyncio.wait_for(task, 0.5) == ["Pehli baat. "]  # max_wait is 1.0 s
    assert not leg.listening


async def test_messages_sent_together_are_spoken_in_one_response():
    leg, _ = await started_leg()
    task = asyncio.create_task(collect(leg, 1, "Boliye"))
    await asyncio.sleep(0.02)
    await leg.speak("Pehli baat")
    await leg.speak("Doosri baat")
    assert await asyncio.wait_for(task, 0.5) == ["Pehli baat. ", "Doosri baat. "]


async def test_a_message_after_the_response_closed_waits_for_the_next_request():
    leg, _ = await started_leg()
    task = asyncio.create_task(collect(leg, 1, "Boliye"))
    await asyncio.sleep(0.02)
    await leg.speak("Pehli baat")
    await asyncio.wait_for(task, 0.5)
    await leg.speak("Baad ki baat")
    assert not leg.listening
    assert await collect(leg, 2, "haan") == ["Baad ki baat. "]


async def test_queued_messages_keep_their_order_when_a_newer_fragment_takes_over():
    leg, _ = await started_leg()
    old = asyncio.create_task(collect(leg, 1, "kuch"))
    await asyncio.sleep(0.02)
    new = asyncio.create_task(collect(leg, 1, "kuch aur"))  # newer fragment owns the reply
    await asyncio.sleep(0.02)
    await leg.speak("Ek")
    await leg.speak("Do")  # both queued before the old request wakes up
    assert await asyncio.wait_for(old, 0.5) == []
    assert await asyncio.wait_for(new, 0.5) == ["Ek. ", "Do. "]


async def test_bolna_leg_cannot_voice_a_hold_line_while_the_user_types():
    assert make_leg().can_hold_line is False


async def test_a_late_fragment_of_a_finished_sentence_is_still_shown():
    """Bolna can send the rest of a sentence after the first part was shown as final."""
    leg, h = await started_leg()
    first = asyncio.create_task(collect(leg, 3, "ऐसे तो नहीं हो सकता।"))
    await asyncio.sleep(0.3)  # settles: the first part is final
    second = asyncio.create_task(collect(leg, 3, "ऐसे तो नहीं हो सकता। कार तो है आपके।"))
    await asyncio.sleep(0.3)
    finals = [t for t, final in h.events if final]
    assert finals == ["ऐसे तो नहीं हो सकता।", "कार तो है आपके।"]
    await first
    await second


def test_every_reply_ends_a_sentence():
    assert end_sentence("Haan ji") == "Haan ji. "
    assert end_sentence("नहीं है") == "नहीं है। "
    assert end_sentence("Kya hua?") == "Kya hua? "


async def test_terminal_status_hangs_up_once():
    leg, h = await started_leg()
    await leg.on_status("in-progress")
    await leg.on_status("call-disconnected")
    await leg.on_status("completed")
    assert h.hung == ["callee_hung_up"]


async def test_hangup_stops_the_call():
    leg, _ = await started_leg()
    await leg.hangup()
    await leg.stopped()
    assert leg.client.stopped == ["exec-1"] and not leg.active


async def test_hangup_keeps_trying_while_bolna_has_not_started_dialling():
    """Bolna refuses a stop until the call exists on the phone network, then dials anyway: the
    user pressed End but the phone rang 4 s later (30 Oct)."""
    leg = make_leg()
    leg.client = FakeBolna(refuse_stops=3)
    h = Heard()
    await leg.start(h.heard, h.hangup)
    await leg.hangup()
    await asyncio.wait_for(leg.stopped(), 1.0)
    assert len(leg.client.stopped) == 4  # three refusals, then accepted


async def test_hangup_before_bolna_answered_the_start_still_stops_the_call():
    class SlowStart(FakeBolna):
        async def start_call(self, agent_id, to, user_data):
            await asyncio.sleep(0.1)
            return await super().start_call(agent_id, to, user_data)

    leg = make_leg()
    leg.client = SlowStart()
    h = Heard()
    starting = asyncio.create_task(leg.start(h.heard, h.hangup))
    await asyncio.sleep(0.02)
    await leg.hangup()  # End pressed while the call is still being placed
    await starting
    await asyncio.wait_for(leg.stopped(), 1.0)
    assert leg.client.stopped == ["exec-1"]


class States:
    def __init__(self):
        self.seen: list[str] = []

    async def __call__(self, state):
        self.seen.append(state)


async def test_progress_follows_bolnas_status_and_each_state_is_reported_once():
    leg, _ = await started_leg()
    states = States()
    leg.on_state = states
    for status in ("queued", "initiated", "ringing", "ringing", "in-progress", "in-progress"):
        await leg.on_status(status)
    assert states.seen == ["ringing", "connected"]


async def test_the_other_person_speaking_proves_the_call_was_answered():
    leg, _ = await started_leg()
    states = States()
    leg.on_state = states
    task = asyncio.create_task(collect(leg, 1, "हेलो"))
    await asyncio.sleep(0.05)
    assert states.seen == ["connected"]
    await leg.hangup()
    await task


@pytest.mark.parametrize(
    "status, reason",
    [
        ("busy", "busy"),
        ("no-answer", "no_answer"),
        ("call-disconnected", "declined"),
        ("canceled", "declined"),
        ("failed", "failed"),
    ],
)
async def test_a_call_that_ends_before_pickup_says_why(status, reason):
    leg, h = await started_leg()
    await leg.on_status("ringing")
    await leg.on_status(status)
    assert h.hung == [reason]


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


async def _bolna_says(ac, status):
    secret = get_settings().webhook_secret
    r = await ac.post(f"/v1/webhooks/bolna?s={secret}", json={"id": "exec-1", "status": status})
    assert r.status_code == 200


async def _placed_call(ac):
    r = await ac.post(
        "/v1/calls", json={"to": "+919876543210"}, headers={"Authorization": f"Bearer {_token()}"}
    )
    assert r.status_code == 200, r.text
    session = registry.get(r.json()["session_id"])
    session.prepare = as_is
    q = session.subscribe()
    await session.start()
    return session, q


async def _drain_until(q, pred, timeout=2.0):
    seen = []
    while True:
        ev = await asyncio.wait_for(q.get(), timeout)
        seen.append(ev)
        if pred(ev):
            return seen


async def test_live_call_flow_captions_reply_and_hangup(env, monkeypatch):
    fake = FakeBolna()
    monkeypatch.setattr("app.services.calls.BolnaClient", lambda settings: fake)
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
        session.leg.max_wait = 0.5  # the reply stream stays open this long for more messages
        q = session.subscribe()
        await session.start()
        assert fake.started[0][2]["call_id"] == call_id
        await _bolna_says(ac, "in-progress")  # the callee picks up
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
    monkeypatch.setattr("app.services.calls.BolnaClient", lambda settings: FakeBolna(fail=message))
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


async def test_connected_is_shown_only_when_the_callee_picks_up(env, monkeypatch):
    monkeypatch.setattr("app.services.calls.BolnaClient", lambda settings: FakeBolna())
    async with async_client() as ac:
        session, q = await _placed_call(ac)
        seen = await _drain_until(q, lambda e: e["t"] == "call.state")
        assert seen[-1]["state"] == "connecting"
        assert q.empty()  # no "connected", no disclosure bubble before anyone answers

        await _bolna_says(ac, "ringing")
        seen = await _drain_until(q, lambda e: e["t"] == "call.state")
        assert seen[-1]["state"] == "ringing" and q.empty()

        await _bolna_says(ac, "in-progress")
        seen = await _drain_until(q, lambda e: e["t"] == "you.final")
        assert [e["state"] for e in seen if e["t"] == "call.state"] == ["connected"]
        assert seen[-1]["source"] == "disclosure"
        await session.end("user")


@pytest.mark.parametrize(
    "status, reason",
    [("busy", "busy"), ("no-answer", "no_answer"), ("call-disconnected", "declined")],
)
async def test_a_call_cut_before_pickup_fails_with_the_reason(env, monkeypatch, status, reason):
    monkeypatch.setattr("app.services.calls.BolnaClient", lambda settings: FakeBolna())
    async with async_client() as ac:
        session, q = await _placed_call(ac)
        await _bolna_says(ac, "ringing")
        await _bolna_says(ac, status)
        seen = await _drain_until(q, lambda e: e["t"] == "call.state" and e["state"] == "failed")
        assert seen[-1]["reason"] == reason
        assert registry.get(session.call_id) is None  # cleaned up


async def test_ending_from_the_app_stops_the_phone_call(env, monkeypatch):
    fake = FakeBolna()
    monkeypatch.setattr("app.services.calls.BolnaClient", lambda settings: fake)
    async with async_client() as ac:
        session, q = await _placed_call(ac)
        await _bolna_says(ac, "in-progress")
        await session.handle({"t": "call.end"})
        await _drain_until(q, lambda e: e["t"] == "call.state" and e["state"] == "ended")
        await asyncio.wait_for(session.leg.stopped(), 1.0)
        assert fake.stopped == ["exec-1"]


# ---------- ending a call that is already live ----------
GOODBYE = "Amit ne call khatam kiya. Namaste. "


async def test_bolna_cannot_stop_a_live_call_so_it_is_asked_once_not_hammered():
    """Bolna's stop only cancels calls that have not started: "Cannot stop call with status:
    in-progress" (30 Oct). Retrying is pointless once the call is live."""
    leg = make_leg()
    leg.client = FakeBolna(live_status="in-progress")
    await leg.start(Heard().heard, Heard().hangup)
    await leg.hangup()
    await asyncio.wait_for(leg.stopped(), 1.0)
    assert leg.client.stopped == ["exec-1"]


async def test_ending_while_bolna_waits_says_goodbye_and_closes_the_request():
    leg, _ = await started_leg()
    task = asyncio.create_task(collect(leg, 1, "Boliye"))
    await asyncio.sleep(0.02)
    await leg.hangup()
    assert await asyncio.wait_for(task, 0.5) == [GOODBYE]


async def test_ending_between_requests_says_goodbye_the_next_time_they_speak():
    leg, _ = await started_leg()
    await leg.hangup()
    assert await collect(leg, 2, "hello?") == [GOODBYE]


async def test_goodbye_is_repeated_a_few_times_if_they_keep_talking_then_stops():
    leg, _ = await started_leg()
    await leg.hangup()
    for turn in (2, 3, 4):
        assert await collect(leg, turn, "hello?") == [GOODBYE]
    assert await collect(leg, 5, "hello?") == []


async def test_typed_messages_after_ending_are_not_spoken():
    leg, _ = await started_leg()
    await leg.hangup()
    await leg.speak("Der se likha hua")
    assert await collect(leg, 2, "haan") == [GOODBYE]


async def test_an_ended_call_stays_registered_until_bolna_reports_it_over():
    bolna_registry.clear()
    leg, _ = await started_leg()
    bolna_registry.add(leg)
    await leg.hangup()
    bolna_registry.release(leg.call_id)  # the session cleans up
    assert bolna_registry.for_execution("exec-1") is leg  # Bolna may still ask for the goodbye
    await leg.on_status("call-disconnected")
    assert bolna_registry.for_execution("exec-1") is None
    bolna_registry.clear()


async def test_an_ended_call_is_released_after_the_linger_time_even_if_bolna_is_silent():
    bolna_registry.clear()
    leg, _ = await started_leg()
    bolna_registry.add(leg)
    await leg.hangup()
    bolna_registry.release(leg.call_id)
    await asyncio.sleep(0.7)  # linger is 0.5 s in tests
    assert bolna_registry.for_execution("exec-1") is None
    bolna_registry.clear()
