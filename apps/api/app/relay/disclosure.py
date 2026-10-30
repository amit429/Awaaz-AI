"""Fixed spoken lines: the disclosure (every relay call, not configurable), keeper, ask-again,
goodbye (the user pressed End)."""

from app.specs import load_json

_FALLBACK_LANG = "en"


def _pick(block: dict[str, str], lang: str, gender: str = "unspecified") -> str:
    """The gendered variant ('hi_m', 'hi_f') when the user's gender is known, else the neutral line."""
    suffix = {"male": "_m", "female": "_f"}.get(gender)
    if suffix and f"{lang}{suffix}" in block:
        return block[f"{lang}{suffix}"]
    return block.get(lang) or block[_FALLBACK_LANG]


def short_lang(lang: str | None) -> str:
    """'hi-IN' to 'hi'."""
    return (lang or _FALLBACK_LANG).split("-")[0].lower()


def disclosure_line(preset: str | None, lang: str, name: str, gender: str = "unspecified") -> str:
    lines = load_json("messages/disclosure_lines.json")
    block = lines.get(preset or "") if preset not in (None, "keeper", "ask_repeat") else None
    if not isinstance(block, dict):
        block = lines["mute"]  # the generic "an assistant is reading out what I type" line
    return _pick(block, short_lang(lang), gender).format(name=name)


def keeper_line(lang: str, name: str, gender: str = "unspecified") -> str:
    block = load_json("messages/disclosure_lines.json")["keeper"]
    return _pick(block, short_lang(lang), gender).format(name=name)


def ask_repeat_line(lang: str) -> str:
    return _pick(load_json("messages/disclosure_lines.json")["ask_repeat"], short_lang(lang))


def goodbye_line(lang: str, name: str) -> str:
    """Said when the user ends the call: Bolna cannot hang up a live call from outside, so this
    is the reply that lets its hangup prompt end the conversation."""
    block = load_json("messages/disclosure_lines.json")["goodbye"]
    return _pick(block, short_lang(lang)).format(name=name)
