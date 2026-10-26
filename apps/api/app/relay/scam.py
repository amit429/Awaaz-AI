"""Scam shield. Rules from specs/data/scam_keywords.csv run on every final caption from the other
person. A strong match (weight 2) triggers at once; a weak one (weight 1) gets an LLM second
opinion. Once triggered the session never speaks 4 to 8 digit runs and the user is warned."""

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.providers.base import Llm
from app.specs import SPECS_DIR

# "We will send an OTP to you" announces a code; it does not ask for one.
BENIGN = re.compile(
    r"\b(we|i)(\s+will|'ll|\s+shall)\s+send\b|\bwill\s+be\s+sent\b|\bsent\s+to\s+your\b|\bshow\s+it\s+to\b",
    re.IGNORECASE,
)

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "is_request": {"type": "boolean"},
        "reason": {
            "type": "string",
            "enum": [
                "otp_request",
                "pin_request",
                "cvv_request",
                "upi_pin",
                "remote_app",
                "none",
                "other",
            ],
        },
        "confidence": {"type": "number"},
    },
    "required": ["is_request", "reason", "confidence"],
}

PROMPT = (
    "You protect a deaf or speech-impaired person on a phone call. Decide whether the other person is "
    "ASKING the user to tell them a secret code (OTP, PIN, UPI PIN, CVV, password) or to install or open "
    "a remote-access app (AnyDesk, TeamViewer, QuickSupport, screen sharing). Mentioning these words "
    "without asking is not a request.\n\nLAST TWO CAPTIONS FROM THE OTHER PERSON:\n{captions}"
)


@dataclass(frozen=True)
class Match:
    reason: str
    weight: int


@dataclass(frozen=True)
class Rule:
    reason: str
    weight: int
    pattern: re.Pattern[str]


@lru_cache
def rules() -> list[Rule]:
    """The spec file is not valid CSV (regexes contain commas): reason and lang come from the
    left, the weight from the right, and everything between is the pattern."""
    out: list[Rule] = []
    lines = (SPECS_DIR / "data/scam_keywords.csv").read_text(encoding="utf-8").splitlines()[1:]
    for line in lines:
        if not line.strip():
            continue
        head, weight = line.rsplit(",", 1)
        reason, _lang, pattern = head.split(",", 2)
        out.append(Rule(reason, int(weight), re.compile(pattern, re.IGNORECASE)))
    return out


def check(text: str) -> Match | None:
    """The strongest rule match in a caption, or None."""
    best: Match | None = None
    benign = bool(BENIGN.search(text))
    for rule in rules():
        if rule.pattern.search(text):
            weight = 1 if benign else rule.weight  # announcements are never a strong match
            if best is None or weight > best.weight:
                best = Match(rule.reason, weight)
    return best


OPENER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"is_scam": {"type": "boolean"}, "confidence": {"type": "number"}},
    "required": ["is_scam", "confidence"],
}
OPENER_PROMPT = (
    "You protect a deaf or speech-impaired person on a phone call with a stranger. Is the other "
    "person likely trying a scam or fraud? Signs: pretending to be a bank, government, police, "
    "courier or company; saying a card, account, SIM or electricity will be blocked or cut; "
    "threatening arrest; promising prizes, refunds or loans; pushing them to click a link, pay, or "
    "share details. An ordinary shop, clinic or friend talking normally is not a scam.\n\n"
    "WHAT THE OTHER PERSON SAID:\n{captions}"
)


async def _opener_opinion(captions: list[str], llm: Llm | None) -> Match | None:
    """Scam openers ("your card will be blocked"). Warned about even before anyone asks for a code,
    because the user cannot hear the pressure in the caller's voice. Fails safe: warn."""
    suspicious = Match("suspicious", 2)
    if llm is None:
        return suspicious
    try:
        out = await llm.complete_json(
            OPENER_PROMPT.format(captions="\n".join(captions[-3:])), schema=OPENER_SCHEMA
        )
    except Exception:  # noqa: BLE001
        return suspicious
    if out.get("is_scam") and float(out.get("confidence", 0)) >= 0.5:
        return suspicious
    return None


async def second_opinion(match: Match, captions: list[str], llm: Llm | None) -> Match | None:
    """Confirm a weak match. Without an answer, wording about secret codes and remote-access apps
    still warns (a missed scam is worse than a false alarm). Scam openers get their own check."""
    if match.weight >= 2:
        return match
    if match.reason == "other":
        return await _opener_opinion(captions, llm)
    fallback = match
    if llm is None:
        return fallback
    try:
        out = await llm.complete_json(
            PROMPT.format(captions="\n".join(captions[-2:])), schema=SCHEMA
        )
    except Exception:  # noqa: BLE001
        return fallback
    if out.get("is_request") and float(out.get("confidence", 0)) >= 0.5:
        reason = out.get("reason")
        return Match(reason if reason not in (None, "none") else match.reason, 2)
    return None
