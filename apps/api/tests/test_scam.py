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
    vague = scam.Match("other", 1)  # "your card will be blocked" alone is not worth a siren
    assert await scam.second_opinion(vague, ["x"], None) is None
    assert await scam.second_opinion(vague, ["x"], Broken()) is None


def test_normal_conversation_is_quiet():
    for text in [
        "हाँ, मिल जाएगी। ₹420 होंगे, शाम 6 बजे तक तैयार।",
        "Your appointment is on Friday at 4 pm.",
        "Delivery Thursday, 950 rupees",
    ]:
        assert scam.check(text) is None
