import asyncio
import json

import httpx

from app.config import Settings
from app.store import Profile
from app.supabase_store import SupabaseStore

URL = "https://proj.supabase.co"


def make_store(handler) -> tuple[SupabaseStore, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def wrapped(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(wrapped))
    return SupabaseStore(Settings(supabase_url=URL, supabase_service_role_key="svc"), client), seen


def body(req: httpx.Request):
    return json.loads(req.content) if req.content else None


async def test_get_profile_combines_both_tables():
    def handler(req):
        if req.url.path.endswith("/profiles"):
            return httpx.Response(200, json=[{"user_id": "u1", "display_name": "Amit"}])
        return httpx.Response(
            200,
            json=[
                {
                    "preset": "mute",
                    "talk_modes": ["type"],
                    "hear_modes": ["audio"],
                    "read_lang": "mr",
                    "type_lang": "hi-Latn",
                }
            ],
        )

    store, seen = make_store(handler)
    p = await store.get_profile("u1")
    assert (p.display_name, p.preset, p.talk_modes, p.read_lang) == ("Amit", "mute", ["type"], "mr")
    assert all(
        r.headers["apikey"] == "svc" and r.headers["Authorization"] == "Bearer svc" for r in seen
    )
    assert {r.url.params["user_id"] for r in seen} == {"eq.u1"}


async def test_get_profile_defaults_when_no_rows():
    store, _ = make_store(lambda req: httpx.Response(200, json=[]))
    p = await store.get_profile("u1")
    assert p.display_name == "Friend" and p.preset is None


async def test_put_profile_upserts_both_tables():
    store, seen = make_store(lambda req: httpx.Response(201))
    await store.put_profile(Profile("u1", "Amit", "hoh", ["voice"], ["clear"], "hi", "hi-Latn"))
    assert [r.url.path.rsplit("/", 1)[-1] for r in seen] == ["profiles", "comm_profiles"]
    assert all(r.headers["Prefer"] == "resolution=merge-duplicates" for r in seen)
    assert body(seen[1])["talk_modes"] == ["voice"]


async def test_every_setting_is_saved_and_read_back():
    """Larger text, speech rate and app language were silently dropped before."""
    store, seen = make_store(lambda req: httpx.Response(201))
    p = Profile("u1", "Amit", "hoh", ["voice"], ["clear"], "hi", "hi", app_lang="ta")
    p.easy_font, p.speech_rate = True, 0.9
    await store.put_profile(p)
    comm = body(seen[1])
    assert (comm["easy_font"], comm["speech_rate"], comm["app_lang"]) == (True, 0.9, "ta")

    row = {**comm, "talk_modes": ["voice"], "hear_modes": ["clear"]}

    def reader(req):
        if req.url.path.endswith("/profiles"):
            return httpx.Response(200, json=[{"display_name": "Amit"}])
        return httpx.Response(200, json=[row])

    store2, _ = make_store(reader)
    back = await store2.get_profile("u1")
    assert (back.easy_font, back.speech_rate, back.app_lang) == (True, 0.9, "ta")


async def test_turns_are_saved_in_the_background_with_the_calls_owner():
    store, seen = make_store(lambda req: httpx.Response(201))
    await store.create_call({"id": "c1", "user_id": "u1", "kind": "relay"})
    await store.add_turn(
        "c1", {"seq": 1, "speaker": "system", "source": "disclosure", "text": "Namaste", "t_ms": 5}
    )
    await asyncio.sleep(0.05)
    turn = body(seen[-1])
    assert seen[-1].url.path.endswith("/turns")
    assert turn["user_id"] == "u1" and turn["seq"] == 1 and turn["entities"] == []


async def test_a_failing_turn_insert_does_not_raise():
    def handler(req):
        return (
            httpx.Response(500, text="boom")
            if req.url.path.endswith("/turns")
            else httpx.Response(201)
        )

    store, _ = make_store(handler)
    await store.create_call({"id": "c1", "user_id": "u1", "kind": "relay"})
    await store.add_turn(
        "c1", {"seq": 1, "speaker": "user", "source": "typed", "text": "hi", "t_ms": 1}
    )
    await asyncio.sleep(0.05)  # logged, not raised into the live call


async def test_auth_user_is_created_or_found():
    def handler(req):
        if req.method == "POST":
            return httpx.Response(422, json={"msg": "already registered"})
        return httpx.Response(200, json={"users": [{"id": "uid-9", "email": "dev@awaaz.local"}]})

    store, _ = make_store(handler)
    assert await store.dev_user() == "uid-9"
    store2, _ = make_store(lambda req: httpx.Response(200, json={"id": "uid-new"}))
    assert await store2.dev_user("x@y.z") == "uid-new"


async def test_seconds_used_today_sums_this_users_durations_since_midnight_ist():
    def handler(req):
        assert req.url.params["user_id"] == "eq.u1"
        assert req.url.params["created_at"].startswith("gte.")
        return httpx.Response(
            200, json=[{"duration_s": 90}, {"duration_s": None}, {"duration_s": 30}]
        )

    store, _ = make_store(handler)
    assert await store.seconds_used_today("u1") == 120
