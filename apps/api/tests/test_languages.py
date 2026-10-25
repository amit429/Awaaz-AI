import asyncio

import httpx
import pytest

from app.auth import current_user
from app.config import Settings, get_settings
from app.main import app
from app.providers.mocks import FakeCallee
from app.relay import registry
from app.relay.legs import MockLeg
from app.relay.session import RelaySession
from app.services import languages, say_prep
from app.services.languages import call_code, make_translator, needs_translation, short
from app.services.profiles import Modes
from app.services.say_prep import prepare_say, script_of
from app.store import InMemoryStore

LIVE = Settings(mock_providers=False, sarvam_api_key="k")


class Llm:
    def __init__(self, out=None, fail=False):
        self.out, self.fail, self.prompts = out, fail, []

    async def complete_json(self, prompt, *, schema):
        self.prompts.append(prompt)
        if self.fail:
            raise RuntimeError("down")
        if "translation" in schema["properties"]:
            return {"translation": self.out}
        return {"language": self.out}


def test_codes():
    assert (
        call_code("hi") == "hi-IN" and call_code("ta-IN") == "ta-IN" and call_code("or") == "od-IN"
    )
    assert call_code(None) == "hi-IN" and call_code("xx") == "hi-IN"
    assert short("od-IN") == "or" and short("hi-IN") == "hi"
    assert (
        not needs_translation("hi-IN", "hi")
        and needs_translation("hi-IN", "hi-Latn")
        and needs_translation("hi-IN", "ta")
    )


def test_script_detection():
    assert script_of("Theek hai 420") == "latin"
    assert script_of("ठीक है ₹420") == "devanagari"
    assert script_of("சரி, நன்றி") == "tamil"
    assert script_of("ঠিক আছে") == "bengali"
    assert script_of("420 ₹") == "none"


async def test_hindi_to_hinglish_is_a_transliteration(monkeypatch):
    async def translit(text, settings, target="hi-IN", source="en-IN"):
        assert (target, source) == ("en-IN", "hi-IN")
        return "haan ji, sharma medical"

    monkeypatch.setattr(languages.sarvam, "transliterate", translit)
    llm = Llm("unused")
    t = make_translator(LIVE, llm)
    assert await t("हाँ जी, शर्मा मेडिकल", "hi-IN", "hi-Latn", "") == "haan ji, sharma medical"
    assert llm.prompts == []


async def test_other_languages_go_through_the_llm_with_context_and_fall_back_to_sarvam(monkeypatch):
    llm = Llm("Telma 40 கிடைக்கும், ₹420")
    t = make_translator(LIVE, llm)
    assert (
        await t("Telma 40 मिल जाएगी, ₹420", "hi-IN", "ta", "BP medicine Telma 40")
        == "Telma 40 கிடைக்கும், ₹420"
    )
    assert (
        "Tamil" in llm.prompts[0]
        and "BP medicine Telma 40" in llm.prompts[0]
        and "as digits" in llm.prompts[0]
    )

    async def sarvam_translate(text, settings, target, source="hi-IN"):
        return f"[{target}] {text}"

    monkeypatch.setattr(languages.sarvam, "translate", sarvam_translate)
    assert await make_translator(LIVE, Llm(fail=True))("x", "hi-IN", "ta", "") == "[ta-IN] x"
    assert await make_translator(LIVE, Llm("y"))("x", "hi-IN", "hi", "") is None  # same language
    assert (
        await make_translator(Settings(mock_providers=True), Llm("y"))("x", "hi-IN", "ta", "")
        is None
    )


async def test_typing_in_the_calls_own_script_is_spoken_and_another_script_needs_confirmation():
    p = await prepare_say("சரி, நன்றி", "ta-IN", LIVE, Llm("unused"))
    assert (p.spoken, p.needs_confirm, p.kind) == ("சரி, நன்றி", False, "as_is")
    p = await prepare_say("சரி, நன்றி", "hi-IN", LIVE, Llm("ठीक है, धन्यवाद"))
    assert (p.spoken, p.needs_confirm, p.kind) == ("ठीक है, धन्यवाद", True, "translated")
    p = await prepare_say("ठीक है", "en-IN", LIVE, Llm("Okay"))
    assert (p.spoken, p.needs_confirm) == ("Okay", True)
    p = await prepare_say("சரி", "hi-IN", LIVE, Llm(fail=True))
    assert p.needs_confirm is True  # never spoken unreviewed


async def test_english_typed_for_an_english_call_is_spoken_as_typed(monkeypatch):
    async def translit(*a, **k):
        return "should not be used"

    monkeypatch.setattr(say_prep.sarvam, "transliterate", translit)
    p = await prepare_say("Please deliver by 7 pm", "en-IN", LIVE, Llm("english"))
    assert (p.spoken, p.needs_confirm) == ("Please deliver by 7 pm", False)


async def _session(translate, read_lang):
    store = InMemoryStore()
    await store.create_call({"id": "c1", "user_id": "u1"})
    s = RelaySession(
        call_id="c1",
        user_id="u1",
        store=store,
        name="R",
        preset="mute",
        call_lang="hi-IN",
        modes=Modes(["type"], ["captions"]),
        leg=MockLeg(FakeCallee.from_fixture("pharmacy"), reply_delay=0.01),
        read_lang=read_lang,
        translate=translate,
    )
    q = s.subscribe()
    await s.start()
    return s, q


async def _collect(q, until, limit=30):
    seen = []
    for _ in range(limit):
        seen.append(await asyncio.wait_for(q.get(), 2))
        if until(seen[-1]):
            return seen
    raise AssertionError([e["t"] for e in seen])


async def test_caption_appears_first_then_its_translation():
    async def translate(text, call_lang, read_lang, notes):
        await asyncio.sleep(0.02)
        return f"[{read_lang}] {text}"

    s, q = await _session(translate, "en")
    seen = await _collect(q, lambda e: e["t"] == "caption.translation")
    kinds = [e["t"] for e in seen]
    assert kinds.index("caption.final") < kinds.index("caption.translation")
    tr = seen[-1]
    assert tr["lang"] == "en" and tr["text"].startswith("[en] हाँ जी") and tr["turn"] == 2
    await s.end()


async def test_switching_caption_language_mid_call_retranslates_recent_captions():
    calls = []

    async def translate(text, call_lang, read_lang, notes):
        calls.append(read_lang)
        return None if read_lang == "hi" else f"[{read_lang}] {text}"

    s, q = await _session(translate, "hi")
    await _collect(q, lambda e: e["t"] == "caption.final")
    await s.handle({"t": "read.set", "lang": "mr"})
    seen = await _collect(q, lambda e: e["t"] == "caption.translation")
    assert {"t": "read.updated", "lang": "mr"} in seen
    assert seen[-1]["lang"] == "mr" and seen[-1]["text"].startswith("[mr]")
    assert s.read_lang == "mr"
    await s.handle({"t": "read.set", "lang": "klingon"})
    assert (await _collect(q, lambda e: e["t"] == "error"))[-1]["code"] == "bad_event"
    await s.end()


async def test_rapid_switching_keeps_every_translation_with_its_language():
    """Switching faster than a translation takes must not lose it or file it under the wrong language."""

    async def translate(text, call_lang, read_lang, notes):
        await asyncio.sleep(0.15)
        return f"[{read_lang}] {text}"

    s, q = await _session(translate, "en")
    await _collect(q, lambda e: e["t"] == "caption.translation")
    for lang in ("mr", "ta", "gu"):  # each switch comes before the previous translation is ready
        await s.handle({"t": "read.set", "lang": lang})
        await asyncio.sleep(0.03)
    got: dict[str, str] = {}
    while set(got) != {"mr", "ta", "gu"}:
        e = await asyncio.wait_for(q.get(), 2)
        if e["t"] == "caption.translation":
            got[e["lang"]] = e["text"]
    assert all(text.startswith(f"[{lang}]") for lang, text in got.items())
    await s.end()


async def test_switching_back_is_instant_and_not_translated_twice():
    calls = []

    async def translate(text, call_lang, read_lang, notes):
        calls.append(read_lang)
        await asyncio.sleep(0.05)
        return f"[{read_lang}] {text}"

    s, q = await _session(translate, "en")
    await _collect(q, lambda e: e["t"] == "caption.translation")
    await s.handle({"t": "read.set", "lang": "ta"})
    await _collect(q, lambda e: e["t"] == "caption.translation" and e["lang"] == "ta")
    before = calls.count("en")
    await s.handle({"t": "read.set", "lang": "en"})
    e = await _collect(q, lambda e: e["t"] == "caption.translation" and e["lang"] == "en")
    assert e[-1]["text"].startswith("[en]")
    assert calls.count("en") == before  # served from what was already translated
    await s.end()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("MOCK_PROVIDERS", "true")
    get_settings.cache_clear()
    registry.clear()
    app.dependency_overrides[current_user] = lambda: "u1"
    yield httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")
    app.dependency_overrides.clear()
    registry.clear()
    get_settings.cache_clear()


PROFILE = {
    "display_name": "Kamla",
    "preset": "hoh",
    "talk_modes": ["voice"],
    "hear_modes": ["captions"],
    "read_lang": "hi-Latn",
    "type_lang": "hi-Latn",
    "app_lang": "mr",
    "easy_font": True,
    "speech_rate": 0.7,
}


async def test_app_language_is_saved_and_reading_language_drives_the_call(client):
    async with client as ac:
        assert (await ac.put("/v1/me", json=PROFILE)).status_code == 200
        me = (await ac.get("/v1/me")).json()
        assert me["profile"]["app_lang"] == "mr" and me["profile"]["read_lang"] == "hi-Latn"
        assert (await ac.put("/v1/me", json={**PROFILE, "app_lang": "fr"})).status_code == 422
        await ac.post(
            "/v1/contacts",
            json={"name": "Netra Clinic", "phone_e164": "+919800000002", "call_lang": "mr"},
        )
        made = (await ac.post("/v1/calls", json={"to": "+919800000002"})).json()
        s = registry.get(made["session_id"])
        assert (
            s.call_lang == "mr-IN" and s.read_lang == "hi-Latn"
        )  # contact's language, user's reading language


async def test_transliterate_endpoint(client, monkeypatch):
    async def translit(text, settings, target="hi-IN", source="en-IN"):
        return "टेल्मा चालीस चाहिए" if target == "hi-IN" else "?"

    monkeypatch.setattr("app.routers.settings.sarvam.transliterate", translit)
    async with client as ac:
        r = await ac.post("/v1/text/transliterate", json={"text": "Telma 40 chahiye", "to": "hi"})
        assert r.json() == {"text": "टेल्मा चालीस चाहिए"}
        assert (
            await ac.post("/v1/text/transliterate", json={"text": "hi", "to": "en"})
        ).json() == {"text": "hi"}
        assert (
            await ac.post("/v1/text/transliterate", json={"text": "hi", "to": "xx"})
        ).json() == {"text": "hi"}
