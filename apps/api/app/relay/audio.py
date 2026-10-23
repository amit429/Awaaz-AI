"""Audio helpers: mu-law <-> PCM16, resampling, 20 ms framing.

Telephony is mu-law 8 kHz; the app and STT use PCM16 16 kHz. NumPy only
(Python 3.13 removed audioop).
"""

from collections.abc import Iterator

import numpy as np

_BIAS = 0x84
_CLIP = 32635


def pcm16_to_mulaw(pcm: np.ndarray) -> bytes:
    x = pcm.astype(np.int32)
    sign = (x < 0).astype(np.int32) * 0x80
    x = np.minimum(np.abs(x), _CLIP) + _BIAS
    exponent = np.floor(np.log2(x)).astype(np.int32) - 7
    exponent = np.clip(exponent, 0, 7)
    mantissa = (x >> (exponent + 3)) & 0x0F
    out = ~(sign | (exponent << 4) | mantissa) & 0xFF
    return out.astype(np.uint8).tobytes()


def mulaw_to_pcm16(data: bytes) -> np.ndarray:
    u = ~np.frombuffer(data, dtype=np.uint8).astype(np.int32) & 0xFF
    sign = u & 0x80
    exponent = (u >> 4) & 0x07
    mantissa = u & 0x0F
    sample = (((mantissa << 3) + _BIAS) << exponent) - _BIAS
    return np.where(sign != 0, -sample, sample).astype(np.int16)


def resample(pcm: np.ndarray, src: int, dst: int) -> np.ndarray:
    """Linear-interpolation resampler with a light low-pass when downsampling."""
    if src == dst:
        return pcm
    x = pcm.astype(np.float64)
    if dst < src:
        r = src // dst  # symmetric triangular kernel: zero phase shift
        k = np.convolve(np.ones(r), np.ones(r))
        k = k / k.sum()
        x = np.convolve(x, k, mode="same")
    n_out = round(len(x) * dst / src)
    pos = np.arange(n_out) * (src / dst)
    out = np.interp(pos, np.arange(len(x)), x)
    return np.clip(np.round(out), -32768, 32767).astype(np.int16)


def frames(data: bytes, size: int, pad: int = 0) -> Iterator[bytes]:
    """Yield fixed-size frames; the last one is padded (default zero byte)."""
    for i in range(0, len(data), size):
        chunk = data[i : i + size]
        if len(chunk) < size:
            chunk += bytes([pad]) * (size - len(chunk))
        yield chunk
