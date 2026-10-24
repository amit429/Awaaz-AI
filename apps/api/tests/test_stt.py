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
