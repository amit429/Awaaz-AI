from app.providers.mocks import MockLlm
from app.relay import scam
from app.specs import SPECS_DIR


def eval_rows() -> list[dict]:
    """scam_eval.csv has unquoted commas inside captions: split id, lang, then expected from the right."""
    rows = []
    lines = (SPECS_DIR / "data/scam_eval.csv").read_text(encoding="utf-8").splitlines()[1:]
    for line in lines:
        head, expected = line.rsplit(",", 1)
        rid, lang, caption = head.split(",", 2)
        rows.append({"id": rid, "lang": lang, "caption": caption, "expected": expected.strip()})
    return rows


def test_eval_set_has_no_missed_requests():
    missed = []
    for r in eval_rows():
        if r["expected"] == "none":
            continue
        m = scam.check(r["caption"])
        if m is None or m.reason != r["expected"]:
            missed.append((r["id"], r["caption"], m))
    assert missed == []  # rule: zero missed requests


def test_false_positives_by_rules_alone_are_listed_and_not_strong():
    fps = {}
    for r in eval_rows():
        if r["expected"] == "none":
            m = scam.check(r["caption"])
            if m:
                fps[r["id"]] = m
    assert set(fps) <= {"11"}  # known: an OTP being announced, not asked for
    assert all(
        m.weight == 1 for m in fps.values()
    )  # weak: the second opinion decides, no instant alarm


def test_keyword_csv_loads_and_patterns_compile():
    assert len(scam.rules()) >= 18
    assert {r.reason for r in scam.rules()} >= {
        "otp_request",
        "pin_request",
        "upi_pin",
        "cvv_request",
        "remote_app",
    }
    header = (SPECS_DIR / "data/scam_keywords.csv").read_text(encoding="utf-8").splitlines()[0]
    assert header == "reason,lang,pattern,weight"


async def test_strong_matches_skip_the_llm():
    m = scam.check("What is your UPI PIN?")
    assert m and m.weight == 2
    assert await scam.second_opinion(m, ["x"], None) == m


async def test_weak_match_needs_the_llm_to_confirm_and_fails_safe():
    weak = scam.Match("otp_request", 1)
    no = MockLlm({"CAPTIONS": {"is_request": False, "reason": "none", "confidence": 0.9}})
    yes = MockLlm({"CAPTIONS": {"is_request": True, "reason": "otp_request", "confidence": 0.8}})
    unsure = MockLlm({"CAPTIONS": {"is_request": True, "reason": "otp_request", "confidence": 0.2}})
    assert await scam.second_opinion(weak, ["We will send an OTP"], no) is None
    assert (await scam.second_opinion(weak, ["share the OTP"], yes)).weight == 2
    assert await scam.second_opinion(weak, ["otp"], unsure) is None

    class Broken:
        async def complete_json(self, *a, **k):
            raise RuntimeError("down")

    assert await scam.second_opinion(weak, ["otp"], Broken()) == weak  # fail safe: warn
    assert await scam.second_opinion(weak, ["otp"], None) == weak
    opener = scam.Match("other", 1)  # "your card will be blocked": warned as a likely scam
    assert await scam.second_opinion(opener, ["x"], None) == scam.Match("suspicious", 2)
    assert await scam.second_opinion(opener, ["x"], Broken()) == scam.Match("suspicious", 2)


def test_normal_conversation_is_quiet():
    for text in [
        "हाँ, मिल जाएगी। ₹420 होंगे, शाम 6 बजे तक तैयार।",
        "Your appointment is on Friday at 4 pm.",
        "Delivery Thursday, 950 rupees",
    ]:
        assert scam.check(text) is None


async def test_scam_openers_from_real_calls_are_flagged():
    """Captions from a real call on 26 October: the caller never asked for an OTP."""
    for text in [
        "आपका कार्ड ब्लॉक होने वाला है।",
        "आपका आईसीआईसीआई बैंक क्रेडिट कार्ड।",
        "Your KYC update is pending, click this link",
        "Aapka sim band ho jayega",
    ]:
        m = scam.check(text)
        assert m is not None and m.reason == "other", text

    class No:
        async def complete_json(self, prompt, *, schema):
            return {"is_scam": False, "confidence": 0.9}

    class Yes:
        async def complete_json(self, prompt, *, schema):
            return {"is_scam": True, "confidence": 0.8}

    m = scam.check("आपका कार्ड ब्लॉक होने वाला है।")
    assert await scam.second_opinion(m, ["आपका कार्ड ब्लॉक होने वाला है।"], Yes()) == scam.Match(
        "suspicious", 2
    )
    assert await scam.second_opinion(m, ["Sharma Medical, credit card chalega"], No()) is None


def test_ordinary_shop_talk_is_not_an_opener():
    for text in [
        "हाँ जी, शर्मा मेडिकल। बोलिए?",
        "₹420 होंगे, शाम 6 बजे तक तैयार।",
        "Kal subah 10 baje aa jaiye",
    ]:
        assert scam.check(text) is None, text
