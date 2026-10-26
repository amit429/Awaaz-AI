"""Smart replies: three short suggestions after each thing the other person says
(specs/prompts/smart_replies.md). Never suggests anything with a 4 to 8 digit run."""

import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.providers.base import Llm
from app.services.languages import gender_note

DIGIT_RUN = re.compile(r"(?<!\d)\d{4,8}(?!\d)")

TYPE_LANG_DESCRIPTION = {
    "hi-Latn": 'Hindi in English letters (romanised Hindi like "Theek hai, rakh dijiye")',
    "hi": "Hindi",
    "en": "English",
    "mr": "Marathi",
}

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"items": {"type": "array", "items": {"type": "string"}, "maxItems": 3}},
    "required": ["items"],
}

SYSTEM = """You suggest replies for {user_name}, who {disability_phrase} and is on a phone call using Awaaz.
Write exactly 3 short replies (max 10 words each) that {user_name} could send next.
- Write in {type_lang_description}.
- {gender_note}
- Match how {user_name} writes (examples below). Be polite and natural for an Indian phone call.
- Reply 1: the most likely answer. Reply 2: a useful follow-up question. Reply 3: "Please repeat" in the same language, unless the last caption is clear and complete, in which case another useful option.
- Use facts from CONTACT NOTES only if relevant. Never invent prices, dates, numbers or personal data.
- Never suggest sharing an OTP, PIN, CVV, password or card number.
Return JSON only."""

USER = """CONTACT: {contact_name}. CONTACT NOTES: {contact_notes}
HOW {user_name} WRITES (last 5 messages): {style_examples}
CONVERSATION (latest last):
{turns}"""


class Suggestions(BaseModel):
    items: list[str] = Field(min_length=1)

    @field_validator("items")
    @classmethod
    def clean(cls, v: list[str]) -> list[str]:
        out = []
        for item in v:
            item = " ".join(item.split())
            if item and len(item) <= 80 and not DIGIT_RUN.search(item) and item not in out:
                out.append(item)
        if not out:
            raise ValueError("no usable suggestions")
        return out[:3]


@dataclass
class ReplyContext:
    user_name: str = "the user"
    disability_phrase: str = "cannot speak"
    type_lang: str = "hi-Latn"
    contact_name: str = "the other person"
    contact_notes: str = "none"
    gender: str = "unspecified"
    typed: list[str] = field(default_factory=list)  # what the user typed on this call


def build_prompt(ctx: ReplyContext, turns: list[tuple[str, str]]) -> str:
    system = SYSTEM.format(
        user_name=ctx.user_name,
        disability_phrase=ctx.disability_phrase,
        type_lang_description=TYPE_LANG_DESCRIPTION.get(ctx.type_lang, "Hindi in English letters"),
        gender_note=gender_note(ctx.gender),
    )
    convo = "\n".join(f"{'them' if who == 'other' else 'you'}: {text}" for who, text in turns[-6:])
    user = USER.format(
        contact_name=ctx.contact_name,
        contact_notes=ctx.contact_notes or "none",
        user_name=ctx.user_name,
        style_examples=" | ".join(ctx.typed[-5:]) or "none yet",
        turns=convo,
    )
    return f"{system}\n\n{user}"


async def suggest(llm: Llm, ctx: ReplyContext, turns: list[tuple[str, str]]) -> list[str]:
    """Up to 3 validated suggestions; one retry on bad output, then none."""
    prompt = build_prompt(ctx, turns)
    for _ in range(2):
        try:
            return Suggestions.model_validate(await llm.complete_json(prompt, schema=SCHEMA)).items
        except (ValidationError, ValueError, KeyError):
            continue
        except Exception:  # noqa: BLE001 - provider down: no suggestions rather than a broken call
            return []
    return []
