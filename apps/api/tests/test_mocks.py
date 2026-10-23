from app.providers.mocks import FakeCallee


def test_pharmacy_script_advances_and_ends():
    c = FakeCallee.from_fixture("pharmacy")
    assert "शर्मा मेडिकल" in c.opening()["text"]
    texts = [c.reply_to("hello")["text"] for _ in range(4)]
    assert len(texts) == 4 and "₹420" in texts[1]
    assert c.reply_to("ok") is None


def test_repeat_pattern_repeats_current_line():
    c = FakeCallee.from_fixture("pharmacy")
    c.opening()
    second = c.reply_to("yes")
    assert c.reply_to("phir se please") == second
    assert c.reply_to("repeat") == second


def test_first_reply_opens_if_not_started():
    c = FakeCallee.from_fixture("bank_scam")
    assert "SBI" in c.reply_to("hi")["text"]


def test_all_fixtures_load():
    for name in ("pharmacy", "bank_scam", "clinic_mr"):
        assert FakeCallee.from_fixture(name).lines
