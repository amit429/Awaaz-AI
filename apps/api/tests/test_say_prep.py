from app.config import Settings
from app.services import say_prep
from app.services.say_prep import prepare_say

S = Settings(mock_providers=False, sarvam_api_key="k")


class FakeLlm:
    """Detection call returns `out`; translation call returns `translation`."""

    def __init__(self, out=None, fail=False):
        self.out, self.fail = out, fail

    async def complete_json(self, prompt, *, schema):
        if self.fail:
            raise RuntimeError("down")
        if "translation" in schema["properties"]:
            return {"translation": self.out["translation"]}
        return {"language": self.out["language"]}


async def fake_translit(text, settings, target="hi-IN", source="en-IN"):
    return "ठीक है, रख दीजिए।"


async def test_native_script_is_spoken_as_is(monkeypatch):
    p = await prepare_say("ठीक है", "hi-IN", S, FakeLlm(fail=True))
    assert (p.spoken, p.needs_confirm, p.kind) == ("ठीक है", False, "as_is")


async def test_hinglish_is_transliterated_without_confirmation(monkeypatch):
    monkeypatch.setattr(say_prep.sarvam, "transliterate", fake_translit)
    p = await prepare_say(
        "Theek hai, rakh dijiye.",
        "hi-IN",
        S,
        FakeLlm({"language": "hindi_roman", "translation": "x"}),
    )
    assert (p.spoken, p.needs_confirm, p.kind) == ("ठीक है, रख दीजिए।", False, "same_language")


async def test_english_is_translated_and_needs_confirmation(monkeypatch):
    monkeypatch.setattr(say_prep.sarvam, "transliterate", fake_translit)
    out = {"language": "english", "translation": "कृपया सात बजे तक पहुँचाइए।"}
    p = await prepare_say("Please deliver by seven", "hi-IN", S, FakeLlm(out))
    assert (p.spoken, p.needs_confirm, p.kind) == ("कृपया सात बजे तक पहुँचाइए।", True, "translated")


async def test_llm_failure_falls_back_to_confirmation(monkeypatch):
    # No obvious words, so the language model is needed; when it fails, ask the user to confirm.
    monkeypatch.setattr(say_prep.sarvam, "transliterate", fake_translit)
    p = await prepare_say("Telma Sharma Medical", "hi-IN", S, FakeLlm(fail=True))
    assert p.needs_confirm is True and p.kind == "same_language"


async def test_obvious_hinglish_never_waits_for_the_language_model(monkeypatch):
    monkeypatch.setattr(say_prep.sarvam, "transliterate", fake_translit)
    p = await prepare_say("Theek hai, rakh dijiye.", "hi-IN", S, FakeLlm(fail=True))
    assert p.needs_confirm is False and p.spoken == "ठीक है, रख दीजिए।"


def test_quick_language():
    q = say_prep.quick_language
    assert q("Telma 40 chahiye") == "hindi_roman"
    assert q("I need Telma 40 please") == "english"
    assert q("mala goli pahije") == "marathi_roman"
    assert q("Telma Sharma Medical") is None
    assert q("kya I need this") is None  # mixed: leave it to the model
