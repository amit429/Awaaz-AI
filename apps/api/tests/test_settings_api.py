import pytest
from fastapi.testclient import TestClient

from app.auth import current_user
from app.config import get_settings
from app.main import app
from app.relay import registry

PROFILE = {
    "display_name": "  Rafiq   Shaikh ",
    "preset": "mute",
    "talk_modes": ["type", "replies", "help"],
    "hear_modes": ["audio", "summary"],
    "read_lang": "hi",
    "type_lang": "hi-Latn",
    "easy_font": False,
    "speech_rate": 0.8,
}
USER = {"id": "u1"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("MOCK_PROVIDERS", "true")
    get_settings.cache_clear()
    registry.clear()
    app.dependency_overrides[current_user] = lambda: USER["id"]
    USER["id"] = "u1"
    yield TestClient(app)
    app.dependency_overrides.clear()
    registry.clear()
    get_settings.cache_clear()


def test_onboarding_state_and_profile_roundtrip(client):
    me = client.get("/v1/me").json()
    assert me["onboarded"] is False and me["profile"]["display_name"] == ""
    assert set(me["presets"]) >= {"mute", "deafspeak", "hoh"}
    r = client.put("/v1/me", json=PROFILE)
    assert r.status_code == 200
    me = client.get("/v1/me").json()
    assert me["onboarded"] is True
    assert me["profile"]["display_name"] == "Rafiq Shaikh"  # whitespace tidied
    assert (
        me["profile"]["talk_modes"] == ["type", "replies", "help"]
        and me["profile"]["speech_rate"] == 0.8
    )


@pytest.mark.parametrize(
    "patch",
    [
        {"preset": "nope"},
        {"talk_modes": []},
        {"hear_modes": ["telepathy"]},
        {"display_name": "   "},
        {"speech_rate": 3},
        {"read_lang": "xx"},
    ],
)
def test_profile_validation(client, patch):
    assert client.put("/v1/me", json={**PROFILE, **patch}).status_code == 422


def test_name_from_profile_is_used_in_the_disclosure(client):
    client.put("/v1/me", json=PROFILE)
    call = client.post("/v1/calls", json={"to": "+919876543210"}).json()
    session = registry.get(call["session_id"])
    assert session.name == "Rafiq Shaikh" and session.preset == "mute"
    assert session.modes.talk == ["type", "replies", "help"]


def test_contacts_crud_is_per_user(client):
    c = client.post(
        "/v1/contacts",
        json={
            "name": "Sharma Medical",
            "phone_e164": "+919800000001",
            "call_lang": "hi",
            "favourite": True,
            "notes": "BP medicine is Telma 40",
        },
    ).json()
    client.post("/v1/contacts", json={"name": "Arif", "phone_e164": "+919800000002"})
    names = [x["name"] for x in client.get("/v1/contacts").json()]
    assert names == ["Sharma Medical", "Arif"]  # favourites first
    upd = client.put(
        f"/v1/contacts/{c['id']}",
        json={"name": "Sharma Medical Store", "phone_e164": "+919800000001"},
    ).json()
    assert upd["name"] == "Sharma Medical Store"
    USER["id"] = "u2"
    assert client.get("/v1/contacts").json() == []
    assert (
        client.put(
            f"/v1/contacts/{c['id']}", json={"name": "x", "phone_e164": "+919800000009"}
        ).status_code
        == 404
    )
    client.delete(f"/v1/contacts/{c['id']}")
    USER["id"] = "u1"
    assert len(client.get("/v1/contacts").json()) == 2  # another user's delete did nothing
    assert client.delete(f"/v1/contacts/{c['id']}").status_code == 204
    assert [x["name"] for x in client.get("/v1/contacts").json()] == ["Arif"]
    assert (
        client.post("/v1/contacts", json={"name": "Bad", "phone_e164": "98765"}).status_code == 422
    )


def test_phrases_crud(client):
    p = client.post(
        "/v1/phrases",
        json={"label": "My address", "text": "Flat 12, Shanti Nagar", "group_name": "Me"},
    ).json()
    assert [x["label"] for x in client.get("/v1/phrases").json()] == ["My address"]
    assert client.delete(f"/v1/phrases/{p['id']}").status_code == 204
    assert client.get("/v1/phrases").json() == []
    assert client.post("/v1/phrases", json={"label": "", "text": "x"}).status_code == 422


def test_call_history_lists_calls_with_contact_names(client):
    client.post("/v1/contacts", json={"name": "Sharma Medical", "phone_e164": "+919800000001"})
    for number in ("+919800000001", "+919800000077"):
        made = client.post("/v1/calls", json={"to": number}).json()
        registry.get(made["session_id"]).ended = True  # one call at a time: finish it first
    history = client.get("/v1/calls").json()
    assert {h["other_number"]: h["name"] for h in history} == {
        "+919800000001": "Sharma Medical",
        "+919800000077": None,
    }
    assert all(h["status"] == "created" for h in history)
