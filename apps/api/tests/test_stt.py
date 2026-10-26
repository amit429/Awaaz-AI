import json

from app.routers.stt import audio_message, sarvam_url, to_client


def test_sarvam_messages_become_small_events():
    assert to_client({"type": "events", "data": {"signal_type": "START_SPEECH"}}) == {
        "t": "vad",
        "signal": "start",
    }
    assert to_client({"type": "events", "data": {"signal_type": "END_SPEECH"}}) == {
        "t": "vad",
        "signal": "end",
    }
    assert to_client({"type": "data", "data": {"transcript": " नमस्ते "}}) == {
        "t": "transcript",
        "text": "नमस्ते",
    }
    assert to_client({"type": "data", "data": {"transcript": "  "}}) is None
    assert to_client({"type": "other"}) is None


def test_audio_is_sent_as_base64_json_and_key_never_in_the_url():
    sent = json.loads(audio_message(b"\x00\x01"))
    assert sent["audio"]["sample_rate"] == 16000 and sent["audio"]["data"] == "AAE="
    url = sarvam_url("hi-IN")
    assert "vad_signals=true" in url and "language_code=hi-IN" in url
    assert "key" not in url


def test_tokens_and_secrets_are_kept_out_of_logs():
    import logging

    from app.main import RedactSecrets

    rec = logging.LogRecord(
        "uvicorn.error",
        20,
        "",
        0,
        '%s - "WebSocket %s" [accepted]',
        ("1.2.3.4", "/v1/relay/abc?token=eyJhbGc.secret&last_turn=0"),
        None,
    )
    RedactSecrets().filter(rec)
    assert (
        "eyJ" not in rec.getMessage()
        and "token=***" in rec.getMessage()
        and "last_turn=0" in rec.getMessage()
    )
    rec = logging.LogRecord(
        "uvicorn.access", 20, "", 0, "%s", ("POST /v1/webhooks/bolna?s=c0bcf05 HTTP/1.1",), None
    )
    RedactSecrets().filter(rec)
    assert "c0bcf05" not in rec.getMessage()


def test_live_voice_keeps_working_when_sarvam_drops_the_stream(monkeypatch):
    """Seen on a real call: Sarvam closed the stream (1011) after the first sentence and nothing
    after it was transcribed. The proxy now reopens the stream and keeps going."""
    import json as _json

    import websockets
    from fastapi.testclient import TestClient

    from app.config import get_settings
    from app.main import create_app
    from app.routers import stt as stt_module

    connections = []

    class FakeUpstream:
        def __init__(self, n):
            self.n, self.sent = n, 0
            self.out = __import__("asyncio").Queue()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def send(self, msg):
            self.sent += 1
            if self.sent == 2:  # one finished sentence per connection, then the drop
                await self.out.put(
                    _json.dumps({"type": "data", "data": {"transcript": f"sentence {self.n}"}})
                )
                await self.out.put(None)

        def __aiter__(self):
            return self

        async def __anext__(self):
            item = await self.out.get()
            if item is None:
                raise websockets.ConnectionClosedError(None, None)
            return item

    def fake_connect(url, additional_headers=None):
        connections.append(url)
        return FakeUpstream(len(connections))

    monkeypatch.setattr(stt_module.websockets, "connect", fake_connect)
    settings = get_settings()
    monkeypatch.setattr(settings, "mock_providers", False)
    monkeypatch.setattr(settings, "sarvam_api_key", "k")
    client = TestClient(create_app())
    token = client.post("/v1/dev/token", json={}).json()["token"]
    with client.websocket_connect(f"/v1/stt/ws?token={token}&lang=hi") as ws:
        got = []
        for _ in range(6):
            ws.send_bytes(b"\x00\x00" * 1600)
            ws.send_bytes(b"\x00\x00" * 1600)
            got.append(ws.receive_json())
            if len(got) == 2:
                break
    assert [g["text"] for g in got] == ["sentence 1", "sentence 2"]
    assert len(connections) >= 2
