import base64
import json

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

client = TestClient(app)


def _secret() -> str:
    return get_settings().webhook_secret


def test_answer_returns_bidirectional_stream_twiml():
    r = client.post(f"/v1/twilio/answer/leg1?s={_secret()}")
    assert r.status_code == 200
    assert "<Connect><Stream url=" in r.text and "/v1/twilio/media/leg1" in r.text
    assert 'name="leg_id" value="leg1"' in r.text


def test_answer_rejects_bad_secret():
    assert client.post("/v1/twilio/answer/leg1?s=nope").status_code == 403


def test_media_socket_echoes_audio():
    payload = base64.b64encode(b"\xff" * 160).decode()
    with client.websocket_connect(f"/v1/twilio/media/leg1?s={_secret()}") as ws:
        ws.send_text(json.dumps({"event": "start", "start": {"streamSid": "MZ1"}}))
        ws.send_text(json.dumps({"event": "media", "media": {"payload": payload}}))
        out = json.loads(ws.receive_text())
    assert out == {"event": "media", "streamSid": "MZ1", "media": {"payload": payload}}
