"""Profile resolution for a call: explicit request, then contact override, then user profile,
then the preset defaults (specs/data/presets.json). Talk and hear are resolved independently."""

from dataclasses import dataclass

from app.specs import load_json


@dataclass(frozen=True)
class Modes:
    talk: list[str]
    hear: list[str]


_DEFAULT_PRESET = "mute"


def _first(*candidates: list[str] | None) -> list[str] | None:
    for c in candidates:
        if c:
            return list(c)
    return None


def resolve_modes(
    *,
    request_talk: list[str] | None = None,
    request_hear: list[str] | None = None,
    contact_talk: list[str] | None = None,
    contact_hear: list[str] | None = None,
    profile_talk: list[str] | None = None,
    profile_hear: list[str] | None = None,
    preset: str | None = None,
) -> Modes:
    presets = load_json("data/presets.json")
    base = presets.get(preset or "") or presets[_DEFAULT_PRESET]
    talk = _first(request_talk, contact_talk, profile_talk, base["talk"])
    hear = _first(request_hear, contact_hear, profile_hear, base["hear"])
    assert talk is not None and hear is not None  # the preset always provides both
    return Modes(talk, hear)


def disability_phrase(preset: str | None) -> str:
    presets = load_json("data/presets.json")
    return (presets.get(preset or "") or presets[_DEFAULT_PRESET])["disability_phrase"]
