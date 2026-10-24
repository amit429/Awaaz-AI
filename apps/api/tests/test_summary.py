from app.services.summary import fallback, summarise

TURNS = [
    {"seq": 1, "speaker": "user", "source": "disclosure", "text": "Namaste", "entities": []},
    {
        "seq": 2,
        "speaker": "other",
        "source": "stt",
        "text": "₹420 होंगे, शाम 6 बजे तैयार",
        "entities": [{"type": "money", "text": "₹420"}, {"type": "time", "text": "शाम 6 बजे"}],
    },
]


async def test_fallback_keeps_numbers_without_a_model():
    s = fallback(TURNS)
    assert [f["value"] for f in s["facts"]] == ["₹420", "शाम 6 बजे"]
    assert "₹420" in s["summary_read_lang"]


async def test_nothing_said_gives_an_empty_summary():
    s = await summarise([TURNS[0]], "hi", None)
    assert s["summary_read_lang"] == "" and s["facts"] == []


class BrokenLlm:
    async def complete_json(self, prompt, *, schema):
        raise RuntimeError("down")


async def test_model_failure_falls_back():
    s = await summarise(TURNS, "hi", BrokenLlm())
    assert s["facts"]


def test_gemini_schema_drops_unsupported_keywords():
    from app.providers.gemini import to_gemini_schema
    from app.services.summary import SCHEMA

    out = str(to_gemini_schema(SCHEMA))
    assert "additionalProperties" not in out and "$schema" not in out and "maxLength" not in out
    iso = SCHEMA["properties"]["facts"]["items"]["properties"]["iso"]
    assert to_gemini_schema(iso) == {"type": "string", "nullable": True}
