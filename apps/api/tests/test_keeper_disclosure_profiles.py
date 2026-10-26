from app.relay.disclosure import ask_repeat_line, disclosure_line, keeper_line
from app.relay.keeper import Keeper
from app.services.profiles import disability_phrase, resolve_modes


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def type_until(c: Clock, k: Keeper, end: float, step: float = 1.0) -> None:
    """Typing events every `step` seconds, as the console sends them while the user types."""
    while c.now + step <= end + 1e-9:
        c.now += step
        k.typing()


def test_keeper_fires_after_5s_of_typing_and_then_waits_20s():
    c = Clock()
    k = Keeper(clock=c)
    k.typing()
    type_until(c, k, 4)
    assert not k.due()
    type_until(c, k, 5)
    assert k.due()
    k.mark_spoken()
    type_until(c, k, 24)
    assert not k.due()  # within 20 s of the last keeper line, however much they type
    type_until(c, k, 25)
    assert k.due()


def test_keeper_stops_when_typing_stops_or_user_sends():
    c = Clock()
    k = Keeper(clock=c)
    k.typing()
    type_until(c, k, 6)
    assert k.due()
    c.now = 11  # the user stopped typing 5 s ago: stale
    assert not k.due()
    k.typing()  # new stretch starts now
    type_until(c, k, 16)
    assert k.due()
    k.reset()
    assert not k.due()


def test_disclosure_lines():
    assert "Rafiq" in disclosure_line("mute", "hi-IN", "Rafiq")
    assert disclosure_line("deafspeak", "mr", "Sana").startswith("नमस्कार, मी Sana")
    assert "assistant" in disclosure_line(
        None, "ta-IN", "Raj"
    )  # falls back to English generic line
    assert keeper_line("en", "Rafiq") == "Rafiq is typing, please hold."
    assert ask_repeat_line("hi").startswith("Maaf kijiye")


def test_resolution_order_request_contact_profile_preset():
    m = resolve_modes(
        request_talk=["voice"],
        contact_talk=["type"],
        contact_hear=["captions"],
        profile_talk=["replies"],
        profile_hear=["audio"],
        preset="mute",
    )
    assert m.talk == ["voice"] and m.hear == ["captions"]
    m = resolve_modes(profile_talk=["replies"], preset="hoh")
    assert m.talk == ["replies"] and m.hear == ["clear", "captions", "summary"]
    m = resolve_modes(preset=None)
    assert m.talk == ["type", "replies", "help"]  # default preset


def test_disability_phrase():
    assert disability_phrase("hoh") == "does not hear well"


def test_spoken_lines_follow_the_users_gender_and_are_neutral_when_unknown():
    from app.relay.disclosure import disclosure_line, keeper_line

    neutral = disclosure_line("deafspeak", "hi-IN", "Amit")
    assert "sakti" not in neutral and "sakta" not in neutral and "Mujhe sunai nahi deta" in neutral
    assert "bol raha hoon" in disclosure_line("mute", "hi-IN", "Amit", "male")
    assert "bol rahi hoon" in disclosure_line("mute", "hi-IN", "Asha", "female")
    assert "Mujhe bolne mein dikkat hai" in disclosure_line("mute", "hi-IN", "Sam")
    assert keeper_line("hi-IN", "Amit", "male").startswith("Amit type kar rahe hain")
    assert keeper_line("hi-IN", "Asha", "female").startswith("Asha type kar rahi hain")
    assert "type ho raha hai" in keeper_line("hi-IN", "Sam")
    assert keeper_line("en-IN", "Sam", "female") == "Sam is typing, please hold."


def test_drafts_and_translations_are_told_the_users_gender():
    from app.services.languages import gender_note
    from app.services.say_prep import _translate_prompt

    assert "masculine" in gender_note("male") and "feminine" in gender_note("female")
    assert "avoid gendered" in gender_note("unspecified")
    assert "feminine" in _translate_prompt("I am coming", "hi-IN", "female")
