"""Entity extraction for captions: money, time, date, phone, quantity. Rules only (no LLM).

Spans are returned for highlighting and for the number chips. Patterns follow
specs/data/entity_patterns.md. Devanagari digits are normalised first (same length, so spans
stay valid in the original text).
"""

import re
from dataclasses import asdict, dataclass

_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

_NUM_WORDS = "एक|दो|दोन|तीन|चार|पाँच|पांच|पाच|छह|छः|सहा|सात|आठ|नौ|नऊ|दस|दहा|ग्यारह|अकरा|बारह|बारा"
_DAYPART = "सुबह|शाम|दोपहर|रात|सकाळी|संध्याकाळी|दुपारी|रात्री"
_TIME_SUFFIX = "am|pm|baje|बजे|वाजता|वाजेपर्यंत"
_WEEKDAY = (
    "monday|tuesday|wednesday|thursday|friday|saturday|sunday|सोमवार|मंगलवार|बुधवार|गुरुवार|"
    "शुक्रवार|शनिवार|रविवार|सोमवारी|मंगळवारी|बुधवारी|गुरुवारी|शुक्रवारी|शनिवारी|रविवारी"
)
_MONTH = "nov|november|नवंबर|नोव्हेंबर|dec|december|दिसंबर|डिसेंबर"

# (type, compiled pattern, group to highlight)
_RULES: list[tuple[str, re.Pattern[str], int]] = [
    ("money", re.compile(r"₹\s?\d[\d,]*"), 0),
    ("money", re.compile(r"\d[\d,]*\s?(?:rs|rupees|rupaye|रुपये|रुपए)", re.IGNORECASE), 0),
    ("phone", re.compile(r"(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}"), 0),
    ("phone", re.compile(r"0\d{2,4}[\s-]?\d{6,8}"), 0),
    (
        "time",
        re.compile(
            rf"(?:(?:{_DAYPART})\s?)?(?:\d{{1,2}}(?::\d{{2}})?|{_NUM_WORDS})\s?(?:{_TIME_SUFFIX})",
            re.IGNORECASE,
        ),
        0,
    ),
    ("time", re.compile(rf"(?:{_DAYPART})\s?\d{{1,2}}"), 0),
    ("date", re.compile(rf"\d{{1,2}}\s?(?:tarikh|तारीख|तारखेला|{_MONTH})", re.IGNORECASE), 0),
    ("date", re.compile(rf"(?:तारीख|तारखेला|date)\s+(\d{{1,2}}|{_NUM_WORDS})", re.IGNORECASE), 1),
    ("date", re.compile(rf"(?:{_WEEKDAY})", re.IGNORECASE), 0),
    ("date", re.compile(r"(?:कल|कळ|उद्या|परसों|kal|parso)(?![ऀ-ॿ])"), 0),
    (
        "quantity",
        re.compile(r"\d+\s?(?:goli|गोली|गोळी|tablet|patta|पत्ता|strip|kg|litre)", re.IGNORECASE),
        0,
    ),
]


@dataclass
class Entity:
    type: str
    text: str
    value: str | float | None
    start: int
    end: int

    def as_dict(self) -> dict:
        return asdict(self)


def _value(kind: str, text: str) -> str | float | None:
    digits = re.sub(r"[^\d]", "", text)
    if kind == "money" and digits:
        return float(digits)
    if kind == "phone" and digits:
        return digits[-10:]
    return None


def extract_entities(text: str) -> list[Entity]:
    norm = text.translate(_DEV_DIGITS)
    found: list[Entity] = []
    for kind, pattern, group in _RULES:
        for m in pattern.finditer(norm):
            start, end = m.span(group)
            found.append(Entity(kind, text[start:end], _value(kind, text[start:end]), start, end))
    # longest first, then earliest; drop anything overlapping a kept span
    found.sort(key=lambda e: (-(e.end - e.start), e.start))
    kept: list[Entity] = []
    for e in found:
        if all(e.end <= k.start or e.start >= k.end for k in kept):
            kept.append(e)
    return sorted(kept, key=lambda e: e.start)
