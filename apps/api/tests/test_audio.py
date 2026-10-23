import numpy as np

from app.relay import audio


def _sine(freq: float, rate: int, ms: int = 200, amp: float = 12000) -> np.ndarray:
    t = np.arange(int(rate * ms / 1000)) / rate
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.int16)


def test_mulaw_roundtrip_error_is_small():
    pcm = _sine(440, 8000)
    back = audio.mulaw_to_pcm16(audio.pcm16_to_mulaw(pcm))
    assert back.shape == pcm.shape
    err = np.abs(back.astype(np.int32) - pcm.astype(np.int32))
    assert err.max() < 600  # mu-law step at amp 12000 is ~512


def test_mulaw_silence_and_bytes_type():
    enc = audio.pcm16_to_mulaw(np.zeros(160, dtype=np.int16))
    assert isinstance(enc, bytes) and len(enc) == 160
    assert np.abs(audio.mulaw_to_pcm16(enc)).max() <= 8


def test_resample_lengths():
    assert len(audio.resample(_sine(300, 8000, 20), 8000, 16000)) == 320
    assert len(audio.resample(_sine(300, 16000, 20), 16000, 8000)) == 160


def test_resample_roundtrip_preserves_tone():
    pcm = _sine(440, 8000)
    back = audio.resample(audio.resample(pcm, 8000, 16000), 16000, 8000)
    mid = slice(20, -20)
    err = np.abs(back[mid].astype(np.int32) - pcm[mid].astype(np.int32))
    assert err.max() < 800


def test_frames_are_20ms_and_pad_last():
    data = bytes(range(256)) * 2  # 512 bytes
    frames = list(audio.frames(data, 160))
    assert [len(f) for f in frames] == [160, 160, 160, 160]
    assert frames[-1] == data[480:] + b"\x00" * (160 - len(data[480:]))
