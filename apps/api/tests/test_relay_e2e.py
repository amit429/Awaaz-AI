import json
import time
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from starlette.websockets import WebSocketDisconnect

import app.store as store_module
from app.config import get_settings
from app.main import app
from app.relay import registry
from app.relay.keeper import Keeper
from app.specs import SPECS_DIR
from app.store import InMemoryStore

SECRET = "t" * 40
SCHEMA = Draft202012Validator(
    json.loads((Path(SPECS_DIR) / "protocol/relay-events.schema.json").read_text(encoding="utf-8"))
)


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)
    monkeypatch.setenv("MOCK_PROVIDERS", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(store_module, "_store", InMemoryStore())
    registry.clear()
    yield
    registry.clear()
    get_settings.cache_clear()


client = TestClient(app)


def token(sub: str = "user-1") -> str:
    return jwt.encode({"sub": sub, "aud": "authenticated"}, SECRET, algorithm="HS256")


def create(sub: str = "user-1", **body) -> dict:
    body = {"to": "+919876543210", **body}
    r = client.post("/v1/calls", json=body, headers={"Authorization": f"Bearer {token(sub)}"})
    assert r.status_code == 200, r.text
    return r.json()


def connect(session_id: str, sub: str = "user-1", last_turn: int = 0):
    return client.websocket_connect(
        f"/v1/relay/{session_id}?token={token(sub)}&last_turn={last_turn}"
    )


def recv(ws, until=lambda e: False, limit: int = 12) -> list[dict]:
    """Read events (each validated against the protocol schema) until `until` matches one."""
    out = []
    for _ in range(limit):
        ev = ws.receive_json()
        SCHEMA.validate(ev)
        out.append(ev)
        if until(ev):
            return out
    raise AssertionError(f"event not seen in {limit}: {[e['t'] for e in out]}")


def is_(t, **kw):
    return lambda e: e["t"] == t and all(e.get(k) == v for k, v in kw.items())


def test_pharmacy_script_end_to_end():
    call = create()
    assert call["ws_url"].endswith(f"/v1/relay/{call['session_id']}")
    with connect(call["session_id"]) as ws:
        first = recv(ws, is_("caption.final"))
        assert [e["t"] for e in first] == ["call.state", "call.state", "you.final", "caption.final"]
        assert first[1]["state"] == "connected"
        assert first[2]["source"] == "disclosure" and "Namaste" in first[2]["text"]
        assert "शर्मा मेडिकल" in first[3]["text"]

        ws.send_json({"t": "user.say", "text": "Telma 40 chahiye", "source": "typed"})
        got = recv(ws, is_("caption.final"))
        assert got[0]["t"] == "you.final" and got[0]["source"] == "typed"
        ws.send_json({"t": "user.say", "text": "Theek hai", "source": "reply"})
        got = recv(ws, is_("caption.final"))
        entities = {(e["type"], e["text"]) for e in got[-1]["entities"]}
        assert ("money", "₹420") in entities and ("time", "शाम 6 बजे") in entities

        ws.send_json({"t": "call.end"})
        recv(ws, is_("call.state", state="ended"))

    saved = client.get(
        f"/v1/calls/{call['session_id']}", headers={"Authorization": f"Bearer {token()}"}
    ).json()
    assert saved["call"]["status"] == "ended"
    sources = [t["source"] for t in saved["turns"]]
    assert sources[:2] == ["disclosure", "stt"] and "typed" in sources and "reply" in sources
    assert [t["seq"] for t in saved["turns"]] == list(range(1, len(saved["turns"]) + 1))


def test_ws_rejects_missing_token_and_other_users():
    call = create()
    with (
        pytest.raises(WebSocketDisconnect) as e1,
        client.websocket_connect(f"/v1/relay/{call['session_id']}"),
    ):
        pass
    assert e1.value.code == 4401
    with pytest.raises(WebSocketDisconnect) as e2, connect(call["session_id"], sub="someone-else"):
        pass
    assert e2.value.code == 4404


def test_bad_and_blocked_events():
    call = create()
    with connect(call["session_id"]) as ws:
        recv(ws, is_("caption.final"))
        ws.send_json({"t": "nope"})
        assert recv(ws, is_("error"))[-1]["code"] == "bad_event"
        ws.send_json({"t": "user.say", "text": "   ", "source": "typed"})
        assert recv(ws, is_("say.blocked"))[-1]["reason"] == "empty"
        ws.send_json({"t": "user.say", "text": "x" * 501, "source": "typed"})
        assert recv(ws, is_("say.blocked"))[-1]["reason"] == "too_long"
        ws.send_text("not json")
        assert recv(ws, is_("error"))[-1]["code"] == "bad_event"


def test_scam_flag_blocks_digit_runs_but_not_short_numbers():
    call = create()
    session = registry.get(call["session_id"])
    with connect(call["session_id"]) as ws:
        recv(ws, is_("caption.final"))
        session.scam = True
        ws.send_json({"t": "user.say", "text": "mera OTP 482913 hai", "source": "typed"})
        assert recv(ws, is_("say.blocked"))[-1]["reason"] == "scam_digits"
        ws.send_json({"t": "user.say", "text": "shaam 6 baje", "source": "typed"})
        assert recv(ws, is_("you.final"))[-1]["text"] == "shaam 6 baje"


def test_keeper_line_only_while_typing():
    call = create()
    session = registry.get(call["session_id"])
    session.keeper = Keeper(after=0.3, every=5.0, stale=1.0)
    with connect(call["session_id"]) as ws:
        recv(ws, is_("caption.final"))
        for _ in range(8):  # about 0.8 s of typing events
            ws.send_json({"t": "user.typing"})
            time.sleep(0.1)
        events = recv(ws, is_("keeper.spoken"))
        assert any(e["t"] == "you.final" and e["source"] == "keeper" for e in events)


def test_no_keeper_without_typing():
    call = create()
    session = registry.get(call["session_id"])
    session.keeper = Keeper(after=0.1, every=0.5, stale=1.0)
    with connect(call["session_id"]) as ws:
        recv(ws, is_("caption.final"))
        time.sleep(0.8)
        ws.send_json({"t": "user.say", "text": "Namaste", "source": "typed"})
        assert [e["t"] for e in recv(ws, is_("caption.final"))] == ["you.final", "caption.final"]


def test_reconnect_replays_missed_turns():
    call = create()
    with connect(call["session_id"]) as ws:
        recv(ws, is_("caption.final"))  # turns 1 (disclosure) and 2 (callee)
    with connect(call["session_id"], last_turn=1) as ws:
        events = recv(ws, is_("caption.final"))
    assert events[0]["t"] == "call.state"
    assert [e["turn"] for e in events if "turn" in e] == [2]


def test_ask_repeat_makes_callee_repeat():
    call = create()
    with connect(call["session_id"]) as ws:
        opening = recv(ws, is_("caption.final"))[-1]["text"]
        ws.send_json({"t": "user.ask_repeat"})
        got = recv(ws, is_("caption.final"))
        assert got[0]["source"] == "ask_repeat"
        assert got[-1]["text"] == opening


def test_mode_set_updates_and_confirms():
    call = create()
    with connect(call["session_id"]) as ws:
        recv(ws, is_("caption.final"))
        ws.send_json({"t": "mode.set", "talk_modes": ["voice"], "hear_modes": ["captions"]})
        ev = recv(ws, is_("mode.updated"))[-1]
        assert ev["talk_modes"] == ["voice"] and ev["hear_modes"] == ["captions"]


def test_call_request_validation_and_live_not_ready(monkeypatch):
    r = client.post(
        "/v1/calls", json={"to": "98765"}, headers={"Authorization": f"Bearer {token()}"}
    )
    assert r.status_code == 422
    monkeypatch.setenv("MOCK_PROVIDERS", "false")
    get_settings.cache_clear()
    r = client.post(
        "/v1/calls", json={"to": "+919876543210"}, headers={"Authorization": f"Bearer {token()}"}
    )
    assert r.status_code == 501


def _prepare_with(session, spoken, needs_confirm, kind="same_language"):
    from app.services.say_prep import Prepared

    async def fake(text: str):
        return Prepared(spoken, needs_confirm, kind)

    session.prepare = fake


def test_same_language_text_is_converted_and_spoken_without_confirmation():
    call = create()
    session = registry.get(call["session_id"])
    _prepare_with(session, "ठीक है, रख दीजिए।", False)
    with connect(call["session_id"]) as ws:
        recv(ws, is_("caption.final"))
        ws.send_json({"t": "user.say", "text": "Theek hai, rakh dijiye.", "source": "typed"})
        got = recv(ws, is_("caption.final"))
        assert (
            got[0]["text"] == "ठीक है, रख दीजिए।" and got[0]["original"] == "Theek hai, rakh dijiye."
        )


def test_translation_needs_one_confirmation_before_speaking():
    call = create()
    session = registry.get(call["session_id"])
    _prepare_with(session, "कृपया सात बजे तक पहुँचाइए।", True, "translated")
    with connect(call["session_id"]) as ws:
        recv(ws, is_("caption.final"))
        ws.send_json({"t": "user.say", "text": "Please deliver by seven", "source": "typed"})
        preview = recv(ws, is_("say.preview"))[-1]
        assert preview["text"] == "कृपया सात बजे तक पहुँचाइए।" and preview["original"].startswith(
            "Please"
        )
        # nothing was spoken yet: no you.final in between
        ws.send_json({"t": "say.confirm", "preview_id": preview["preview_id"]})
        got = recv(ws, is_("caption.final"))
        assert got[0]["t"] == "you.final" and got[0]["text"] == "कृपया सात बजे तक पहुँचाइए।"
        ws.send_json({"t": "say.confirm", "preview_id": preview["preview_id"]})
        assert recv(ws, is_("error"))[-1]["code"] == "unknown_preview"


def test_digit_block_checks_what_was_typed_not_the_converted_text():
    call = create()
    session = registry.get(call["session_id"])
    _prepare_with(session, "मेरा ओटीपी चार आठ दो नौ एक तीन है", False)  # digits spelled out
    session.scam = True
    with connect(call["session_id"]) as ws:
        recv(ws, is_("caption.final"))
        ws.send_json({"t": "user.say", "text": "mera OTP 482913 hai", "source": "typed"})
        assert recv(ws, is_("say.blocked"))[-1]["reason"] == "scam_digits"
