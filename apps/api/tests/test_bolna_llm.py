import json

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.relay.dev_bridge import bridge
from app.routers.bolna_llm import current_turn

client = TestClient(app)
AUTH = {"Authorization": f"Bearer {get_settings().webhook_secret}"}


def _events(text: str) -> list[str]:
    return [line[6:] for line in text.splitlines() if line.startswith("data: ")]


def test_requires_bearer():
    assert client.get("/v1/llm/models").status_code == 401
    assert client.get("/v1/llm/models", headers=AUTH).json()["data"][0]["id"] == "awaaz-relay"


def test_current_turn_merges_trailing_user_fragments():
    msgs = [
        {"role": "system", "content": "x"},
        {"role": "assistant", "content": "welcome"},
        {"role": "user", "content": "हाँ जी।"},
        {"role": "user", "content": "शर्मा मेडिकल।"},
    ]
    assert current_turn(msgs) == (1, "हाँ जी। शर्मा मेडिकल।")
    msgs += [{"role": "assistant", "content": "reply"}, {"role": "user", "content": "बोलिए"}]
    assert current_turn(msgs) == (2, "बोलिए")


def test_caption_recorded_and_typed_reply_streamed():
    bridge.captions.clear()
    bridge.say("Theek hai")
    body = {
        "messages": [{"role": "assistant", "content": "hi"}, {"role": "user", "content": "Namaste"}]
    }
    r = client.post("/v1/llm/chat/completions", json=body, headers=AUTH)
    ev = _events(r.text)
    assert ev[-1] == "[DONE]"
    assert json.loads(ev[0])["choices"][0]["delta"]["content"].strip() == "Theek hai"
    assert json.loads(ev[1])["choices"][0]["finish_reason"] == "stop"
    assert bridge.captions == [{"turn": 1, "text": "Namaste"}]


def test_console_page_is_gated():
    assert client.get("/dev/console").status_code == 404
    page = client.get(f"/dev/console?s={get_settings().webhook_secret}")
    assert page.status_code == 200 and "Awaaz dev console" in page.text
