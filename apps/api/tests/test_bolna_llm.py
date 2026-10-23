import json

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.relay.dev_bridge import bridge

client = TestClient(app)
AUTH = {"Authorization": f"Bearer {get_settings().webhook_secret}"}


def _events(text: str) -> list[str]:
    return [line[6:] for line in text.splitlines() if line.startswith("data: ")]


def test_requires_bearer():
    assert client.get("/v1/llm/models").status_code == 401
    assert client.get("/v1/llm/models", headers=AUTH).json()["data"][0]["id"] == "awaaz-relay"


def test_caption_recorded_and_typed_reply_streamed():
    bridge.captions.clear()
    client.post("/v1/dev/say", json={"text": "Theek hai"}, headers=AUTH)
    body = {
        "messages": [{"role": "system", "content": "x"}, {"role": "user", "content": "Namaste"}]
    }
    r = client.post("/v1/llm/chat/completions", json=body, headers=AUTH)
    ev = _events(r.text)
    assert ev[-1] == "[DONE]"
    assert json.loads(ev[0])["choices"][0]["delta"]["content"] == "Theek hai"
    assert json.loads(ev[1])["choices"][0]["finish_reason"] == "stop"
    assert bridge.captions == ["Namaste"]
