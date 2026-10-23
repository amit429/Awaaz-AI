import asyncio
import hashlib
import hmac
import json

import httpx
import pytest

import app.store as store_module
from app.config import get_settings
from app.main import app
from app.providers import meta_wa
from app.relay import registry
from app.routers import webhooks_wa
from app.services import wa_bot
from app.store import InMemoryStore

PAYLOAD = {
    "entry": [
        {
            "changes": [
                {
                    "value": {
                        "contacts": [{"wa_id": "919800000001", "profile": {"name": "Amit"}}],
                        "messages": [
                            {
                                "from": "919800000001",
                                "id": "wamid.1",
                                "type": "text",
                                "text": {"body": "call practice pharmacy"},
                            },
                            {
                                "from": "919800000001",
                                "id": "wamid.2",
                                "type": "audio",
                                "audio": {"id": "media-9"},
                            },
                        ],
                    }
                },
                {"value": {"statuses": [{"id": "wamid.0", "status": "delivered"}]}},
            ]
        }
    ]
}


def sign(secret: str, raw: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()


def test_parse_webhook_extracts_messages_and_skips_statuses():
    msgs = meta_wa.parse_webhook(PAYLOAD)
    assert [(m.wa_id, m.type, m.text, m.name) for m in msgs] == [
        ("919800000001", "text", "call practice pharmacy", "Amit"),
        ("919800000001", "audio", "", "Amit"),
    ]
    assert msgs[1].media_url == "media-9"


def test_signature_check():
    raw = b'{"a":1}'
    assert meta_wa.valid_signature("sec", raw, sign("sec", raw))
    assert not meta_wa.valid_signature("sec", raw, sign("other", raw))
    assert not meta_wa.valid_signature("sec", raw, None)
    assert not meta_wa.valid_signature("sec", raw, "sha1=abc")


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("WA_PROVIDER", "log")
    monkeypatch.setenv("META_WA_APP_SECRET", "appsecret")
    monkeypatch.setenv("META_WA_VERIFY_TOKEN", "verify-me")
    monkeypatch.setenv("MOCK_PROVIDERS", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(store_module, "_store", InMemoryStore())
    registry.clear()
    wa_bot.reset_bot()
    webhooks_wa.reset_sender()
    yield
    registry.clear()
    wa_bot.reset_bot()
    webhooks_wa.reset_sender()
    get_settings.cache_clear()


def client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_verification_handshake(env):
    async with client() as ac:
        ok = await ac.get(
            "/v1/webhooks/wa/meta",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "verify-me",
                "hub.challenge": "12345",
            },
        )
        assert ok.status_code == 200 and ok.text == "12345"
        bad = await ac.get(
            "/v1/webhooks/wa/meta",
            params={"hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "1"},
        )
        assert bad.status_code == 403


async def test_signed_message_reaches_the_bot_and_unsigned_is_refused(env):
    raw = json.dumps(PAYLOAD).encode()
    async with client() as ac:
        bad = await ac.post(
            "/v1/webhooks/wa/meta", content=raw, headers={"X-Hub-Signature-256": "sha256=00"}
        )
        assert bad.status_code == 403
        ok = await ac.post(
            "/v1/webhooks/wa/meta",
            content=raw,
            headers={"X-Hub-Signature-256": sign("appsecret", raw)},
        )
        assert ok.status_code == 200
        for _ in range(100):
            out = (await ac.get("/v1/dev/wa/outbox?wa_id=919800000001")).json()["messages"]
            if any("*Them:*" in t for t in out):
                break
            await asyncio.sleep(0.02)
        assert any("Calling a practice caller" in t for t in out) and any(
            "*Them:*" in t for t in out
        )
        assert any("Voice notes are coming soon" in t for t in out)
        await ac.post("/v1/dev/wa", json={"wa_id": "919800000001", "text": "end"})


async def test_sender_posts_to_the_graph_api(monkeypatch):
    from app.config import Settings

    seen = {}

    class FakeClient:
        def __init__(self, *a, **k): ...
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a): ...
        async def post(self, url, json=None, headers=None):
            seen.update(url=url, json=json, headers=headers)
            return httpx.Response(200, json={"messages": [{"id": "x"}]})

    monkeypatch.setattr(meta_wa.httpx, "AsyncClient", FakeClient)
    sender = meta_wa.MetaSender(Settings(meta_wa_token="tok", meta_wa_phone_id="123"))
    await sender.send("919800000001", "hello")
    assert seen["url"] == "https://graph.facebook.com/123/messages"
    assert seen["json"]["to"] == "919800000001" and seen["json"]["text"]["body"] == "hello"
    assert seen["headers"]["Authorization"] == "Bearer tok"
