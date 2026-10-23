"""Fixed spoken lines: the disclosure (every relay call, not configurable), keeper, ask-again."""

from app.specs import load_json

_FALLBACK_LANG = "en"


def _pick(block: dict[str, str], lang: str) -> str:
    return block.get(lang) or block[_FALLBACK_LANG]


def short_lang(lang: str | None) -> str:
    """'hi-IN' to 'hi'."""
    return (lang or _FALLBACK_LANG).split("-")[0].lower()


def disclosure_line(preset: str | None, lang: str, name: str) -> str:
    lines = load_json("messages/disclosure_lines.json")
    block = lines.get(preset or "") if preset not in (None, "keeper", "ask_repeat") else None
    if not isinstance(block, dict):
        block = lines["mute"]  # the generic "an assistant is reading out what I type" line
    return _pick(block, short_lang(lang)).format(name=name)


def keeper_line(lang: str, name: str) -> str:
    return _pick(load_json("messages/disclosure_lines.json")["keeper"], short_lang(lang)).format(
        name=name
    )


def ask_repeat_line(lang: str) -> str:
    return _pick(load_json("messages/disclosure_lines.json")["ask_repeat"], short_lang(lang))
