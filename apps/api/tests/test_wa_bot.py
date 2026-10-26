import asyncio

import httpx
import pytest

import app.store as store_module
from app.config import Settings, get_settings
from app.main import app
from app.providers import twilio_wa
from app.providers.twilio_wa import Inbound, LogSender
from app.relay import bolna_registry, registry
from app.routers import webhooks_wa
from app.services import wa_bot
from app.services.say_prep import Prepared
from app.services.wa_bot import WaBot, bold_entities, to_e164
from app.store import InMemoryStore

WA = "919800000001"


@pytest.fixture(autouse=True)
def clean():
    registry.clear()
    bolna_registry.clear()
    wa_bot.reset_bot()
    webhooks_wa.reset_sender()
    yield
    registry.clear()
    bolna_registry.clear()
    wa_bot.reset_bot()
    webhooks_wa.reset_sender()


def make_bot(**settings) -> tuple[WaBot, LogSender]:
    sender = LogSender()
    return WaBot(Settings(mock_providers=True, **settings), InMemoryStore(), sender), sender


def text(s: str, wa_id: str = WA) -> Inbound:
    return Inbound(wa_id=wa_id, type="text", text=s, name="Amit")


async def until(sender: LogSender, needle: str, timeout: float = 2.0) -> list[str]:
    for _ in range(int(timeout / 0.02)):
        if any(needle in t for t in sender.texts()):
            return sender.texts()
        await asyncio.sleep(0.02)
    raise AssertionError(f"{needle!r} not sent: {sender.texts()}")


def test_number_parsing_and_bold_entities():
    assert to_e164("98765 43210") == "+919876543210"
    assert to_e164("+1 650 555 0100") == "+16505550100"
    assert to_e164("919876543210") == "+919876543210"
    assert to_e164("12345") is None
    assert bold_entities("हाँ, मिल जाएगी। ₹420 होंगे, शाम 6 बजे तक तैयार।") == (
        "हाँ, मिल जाएगी। *₹420* होंगे, *शाम 6 बजे* तक तैयार।"
    )


async def test_help_for_unknown_text_and_non_text():
    bot, sender = make_bot()
    await bot.handle(text("hello"))
    assert "call 98765 43210" in sender.texts()[0]
    await bot.handle(Inbound(wa_id=WA, type="audio"))
    assert "Voice notes are coming soon" in sender.texts()[-1]


async def test_practice_call_conversation_end_to_end():
    bot, sender = make_bot()
    await bot.handle(text("call practice pharmacy"))
    texts = await until(sender, "*Them:*")
    assert "Calling a practice caller" in texts[0]
    assert any(
        "Awaaz told them" in t and "Amit" in t for t in texts
    )  # disclosure uses the WhatsApp name
    assert any("शर्मा मेडिकल" in t for t in texts)

    await bot.handle(text("Telma 40 chahiye"))
    await until(sender, "Telma 40, कितनी")
    await bot.handle(text("Theek hai"))
    texts = await until(sender, "*₹420*")
    assert "*शाम 6 बजे*" in texts[-1]

    await bot.handle(text("end"))
    texts = await until(sender, "Call ended")
    assert "You ended the call." in texts[-1]
    await asyncio.sleep(0.05)
    assert bot.calls == {}  # the next message starts fresh


async def test_commands_again_hold_and_busy():
    bot, sender = make_bot()
    await bot.handle(text("call practice pharmacy"))
    await until(sender, "*Them:*")
    await bot.handle(text("again"))
    await until(sender, "Maaf kijiye")
    await bot.handle(text("hold"))
    await until(sender, "type ho raha hai")
    await bot.handle(text("help"))
    assert "again" in sender.texts()[-1]
    await bot.handle(text("end"))
    await until(sender, "Call ended")


async def test_translation_needs_ok_then_is_spoken():
    bot, sender = make_bot()
    await bot.handle(text("call practice pharmacy"))
    await until(sender, "*Them:*")
    call = bot.calls[WA]

    async def fake(t: str) -> Prepared:
        return Prepared("कृपया सात बजे तक पहुँचाइए।", True, "translated")

    call.session.prepare = fake
    await bot.handle(text("Please deliver by seven"))
    await until(sender, "Say this?")
    assert call.pending_preview
    await bot.handle(text("ok"))
    await until(sender, "Said:")  # converted text is echoed once it is spoken
    assert call.pending_preview is None

    await bot.handle(text("Please deliver by seven"))
    for _ in range(100):  # wait for the second preview message
        if sum("Reply *ok*" in t for t in sender.texts()) == 2:
            break
        await asyncio.sleep(0.02)
    n = len(sender.texts())
    await bot.handle(text("cancel"))
    assert sender.texts()[n] == "Okay, not sent."
    await bot.handle(text("end"))


async def test_cannot_start_a_live_call_when_telephony_is_not_configured():
    sender = LogSender()
    bot = WaBot(
        Settings(mock_providers=False, bolna_api_key="", bolna_relay_agent_id=""),
        InMemoryStore(),
        sender,
    )
    await bot.handle(text("call 98765 43210"))
    assert "couldn’t start that call" in sender.texts()[-1]
    assert bot.calls == {}


async def test_users_are_separate_and_numbers_are_masked():
    bot, sender = make_bot()
    await bot.handle(text("call practice clinic", wa_id="919800000002"))
    await until(sender, "*Them:*")
    await bot.handle(text("hello", wa_id="919800000003"))  # a different user is idle: gets help
    assert "call 98765 43210" in sender.texts()[-1]
    assert set(bot.calls) == {"919800000002"}
    await bot.handle(text("end", wa_id="919800000002"))


# ---------- the webhook ----------
@pytest.fixture
def webhook_env(monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "tok")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.test")
    monkeypatch.setenv("WA_PROVIDER", "log")
    monkeypatch.setenv("MOCK_PROVIDERS", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(store_module, "_store", InMemoryStore())
    yield get_settings()
    get_settings.cache_clear()


def client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def signed(settings, params):
    url = f"https://example.test/v1/webhooks/wa/twilio_sandbox?s={settings.webhook_secret}"
    return url, {"X-Twilio-Signature": twilio_wa.twilio_signature("tok", url, params)}


async def test_webhook_accepts_signed_request_and_replies(webhook_env):
    params = {
        "From": f"whatsapp:+{WA}",
        "Body": "hello",
        "ProfileName": "Amit",
        "MessageSid": "SM1",
        "NumMedia": "0",
    }
    _, headers = signed(webhook_env, params)
    async with client() as ac:
        r = await ac.post(
            f"/v1/webhooks/wa/twilio_sandbox?s={webhook_env.webhook_secret}",
            data=params,
            headers=headers,
        )
        assert r.status_code == 200 and "<Response>" in r.text
        await asyncio.sleep(0.1)
        out = await ac.get(f"/v1/dev/wa/outbox?wa_id={WA}")
    assert "call 98765 43210" in out.json()["messages"][0]


async def test_webhook_rejects_bad_secret_and_bad_signature(webhook_env):
    params = {"From": f"whatsapp:+{WA}", "Body": "hello", "NumMedia": "0"}
    _, headers = signed(webhook_env, params)
    async with client() as ac:
        r = await ac.post("/v1/webhooks/wa/twilio_sandbox?s=nope", data=params, headers=headers)
        assert r.status_code == 403
        r = await ac.post(
            f"/v1/webhooks/wa/twilio_sandbox?s={webhook_env.webhook_secret}",
            data=params,
            headers={"X-Twilio-Signature": "bad"},
        )
        assert r.status_code == 403
        r = await ac.post(
            f"/v1/webhooks/wa/twilio_sandbox?s={webhook_env.webhook_secret}", data=params
        )
        assert r.status_code == 403


def test_normalise_twilio_payload():
    m = twilio_wa.normalise(
        {"From": "whatsapp:+919800000001", "Body": "hi", "ProfileName": "Amit", "NumMedia": "0"}
    )
    assert (m.wa_id, m.type, m.text, m.name) == ("919800000001", "text", "hi", "Amit")
    a = twilio_wa.normalise(
        {
            "From": "whatsapp:+919800000001",
            "NumMedia": "1",
            "MediaContentType0": "audio/ogg",
            "MediaUrl0": "https://m/1",
        }
    )
    assert a.type == "audio" and a.media_url == "https://m/1"
    assert twilio_wa.valid_signature(
        "tok",
        "https://x/y",
        {"a": "1"},
        twilio_wa.twilio_signature("tok", "https://x/y", {"a": "1"}),
    )
