"""Turn what the user typed into what is spoken on the call.

Same language as the call (any spelling or script): converted to native script and spoken
without confirmation. Another language: translated and flagged `needs_confirm` (rule: translated
text is shown to the user and spoken only after they confirm).
"""

import asyncio
import re
from dataclasses import dataclass

from app.config import Settings
from app.providers import sarvam
from app.providers.base import Llm
from app.services.languages import SPOKEN, short

# Unicode blocks of Indian scripts, and the script each spoken language is written in
_BLOCKS = [
    (0x0900, 0x097F, "devanagari"),
    (0x0980, 0x09FF, "bengali"),
    (0x0A00, 0x0A7F, "gurmukhi"),
    (0x0A80, 0x0AFF, "gujarati"),
    (0x0B00, 0x0B7F, "odia"),
    (0x0B80, 0x0BFF, "tamil"),
    (0x0C00, 0x0C7F, "telugu"),
    (0x0C80, 0x0CFF, "kannada"),
    (0x0D00, 0x0D7F, "malayalam"),
]
SCRIPT_OF_LANG = {
    "hi": "devanagari",
    "mr": "devanagari",
    "bn": "bengali",
    "pa": "gurmukhi",
    "gu": "gujarati",
    "or": "odia",
    "ta": "tamil",
    "te": "telugu",
    "kn": "kannada",
    "ml": "malayalam",
    "en": "latin",
}


def script_of(text: str) -> str:
    """The dominant script of the letters in `text`: latin, devanagari, tamil, ... or none."""
    counts: dict[str, int] = {}
    for ch in text:
        if not ch.isalpha():
            continue
        cp = ord(ch)
        if ch.isascii():
            name = "latin"
        else:
            name = next((n for lo, hi, n in _BLOCKS if lo <= cp <= hi), "other")
        counts[name] = counts.get(name, 0) + 1
    return max(counts, key=counts.__getitem__) if counts else "none"


# Words that settle the language of text typed in English letters without asking a model.
# Words that mean something in both languages are left out on purpose.
def _words(text: str) -> frozenset[str]:
    return frozenset(text.split())


_HINDI = _words(
    "hai hain hoon kya kyun kyon kaise kab kahan kaun kitna kitni kitne mujhe mere meri mera aap "
    "aapko aapka aapki tum tumhe nahi nahin haan ji chahiye chahie dijiye kijiye bataiye batao "
    "dena lena karna karo ka ki ke ko se mein par aur ya bhi toh abhi kal aaj subah shaam raat baje "
    "rupaye rupay goli dawai dawa theek thik accha achha wala wali sahi paisa tak pehle baad ruko "
    "sunai samajh lijiye dijiyega boliye bolo chalega hoga hogi honge milega milegi bhejiye bhej "
    "kuch sab liye lagega"
)
_MARATHI = _words(
    "aahe ahe aahet pahije pahijet mala tumhala kay kaay kuthe kiti kasa kashi zhala jhala mhanje "
    "tumhi amhi aamhi dya saanga sanga vaajta vajta tumhi aahes nako hoy"
)
_ENGLISH = _words(
    "the is are am was i you we he she it need want please what how when where my your can could "
    "will would does did have has of for and with this that in on at not yes okay thank thanks "
    "hello medicine tablet tablets price time today tomorrow give send call us them if but be been "
    "an morning evening night delivery address number"
)
_WORD = re.compile(r"[a-z]+")


def quick_language(text: str) -> str | None:
    """hindi_roman, marathi_roman or english when the words make it obvious, else None."""
    words = _WORD.findall(text.lower())
    hi = sum(w in _HINDI for w in words)
    mr = sum(w in _MARATHI for w in words)
    en = sum(w in _ENGLISH for w in words)
    if mr and mr >= hi and not en:
        return "marathi_roman"
    if hi and en == 0:
        return "hindi_roman"
    if en and hi == 0 and mr == 0:
        return "english"
    return None


LANGS = ["hindi_roman", "marathi_roman", "english", "other"]
DETECT_SCHEMA = {
    "type": "object",
    "properties": {"language": {"type": "string", "enum": LANGS}},
    "required": ["language"],
}
TRANSLATE_SCHEMA = {
    "type": "object",
    "properties": {"translation": {"type": "string"}},
    "required": ["translation"],
}

CALL_LANG_NAME = {code: name for name, code in SPOKEN.values()}
SAME_LANG = {"hi-IN": "hindi_roman", "mr-IN": "marathi_roman", "en-IN": "english"}


@dataclass
class Prepared:
    spoken: str
    needs_confirm: bool
    kind: str  # "as_is" | "same_language" | "translated"
    detected: str | None = None


def _detect_prompt(text: str) -> str:
    return (
        "Which language is this text typed in? hindi_roman (Hindi in English letters), "
        "marathi_roman (Marathi in English letters), english, or other.\n\nText: " + text
    )


def _translate_prompt(text: str, call_lang: str) -> str:
    name = CALL_LANG_NAME.get(call_lang, "Hindi")
    return (
        f"Translate this text faithfully into {name}, in its native script, to be spoken aloud on a "
        "phone call. Keep every number, name and medicine name exactly; do not add or remove "
        "information.\n\nText: " + text
    )


async def prepare_say(text: str, call_lang: str, settings: Settings, llm: Llm) -> Prepared:
    text = text.strip()
    if not text:
        return Prepared("", False, "as_is")
    script = script_of(text)
    if script == "none":  # digits and punctuation only
        return Prepared(text, False, "as_is")
    if script != "latin":
        if script == SCRIPT_OF_LANG.get(short(call_lang)):
            return Prepared(text, False, "as_is")  # already in the call's own script
        # Typed in another Indian script (for example Tamil on a Hindi call): translate, confirm.
        try:
            out = await llm.complete_json(
                _translate_prompt(text, call_lang), schema=TRANSLATE_SCHEMA
            )
            return Prepared(out["translation"], True, "translated", script)
        except Exception:  # noqa: BLE001 - never speak something unreviewed
            return Prepared(text, True, "translated", script)
    # Latin letters. Obvious cases skip the language model, which is what made sending slow.
    quick = quick_language(text)
    if quick is None:
        translit, detected = await asyncio.gather(
            sarvam.transliterate(text, settings, target=call_lang),
            llm.complete_json(_detect_prompt(text), schema=DETECT_SCHEMA),
            return_exceptions=True,
        )
    else:
        detected = {"language": quick}
        if quick == SAME_LANG.get(call_lang) and quick != "english":
            try:
                translit = await sarvam.transliterate(text, settings, target=call_lang)
            except Exception as exc:  # noqa: BLE001
                translit = exc
        else:
            translit = text  # unused: translated or spoken as typed
    translit_ok = not isinstance(translit, BaseException)
    if isinstance(detected, BaseException) or "language" not in detected:
        # Cannot tell: show the transliteration and ask.
        return Prepared(translit if translit_ok else text, True, "same_language", None)
    language = detected["language"]
    if language == SAME_LANG.get(call_lang):
        if language == "english":  # English typed for an English call: speak it as typed
            return Prepared(text, False, "as_is", language)
        if translit_ok:
            return Prepared(translit, False, "same_language", language)
    try:
        out = await llm.complete_json(_translate_prompt(text, call_lang), schema=TRANSLATE_SCHEMA)
        return Prepared(out["translation"], True, "translated", language)
    except Exception:  # noqa: BLE001 - provider failure must not speak anything unreviewed
        return Prepared(translit if translit_ok else text, True, "same_language", language)


def make_preparer(settings: Settings, call_lang: str, llm: Llm):
    """The session's preparer: conversion in live mode, pass-through in mock mode."""

    async def prepare(text: str) -> Prepared:
        if settings.mock_providers:
            return Prepared(text, False, "as_is")
        return await prepare_say(text, call_lang, settings, llm)

    return prepare
