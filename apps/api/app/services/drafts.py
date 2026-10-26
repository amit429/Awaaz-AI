"""Help me say it: a few words become one short, polite sentence (specs/prompts/help_me_say.md).
The draft is shown to the user and spoken only after they tap Say it (rule 3)."""

import re
from dataclasses import dataclass

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.providers.base import Llm
from app.services.languages import gender_note
from app.services.replies import TYPE_LANG_DESCRIPTION

DIGIT_RUN = re.compile(r"(?<!\d)\d{4,8}(?!\d)")

SCHEMA = {
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "lang": {"type": "string"},
        "changed_meaning_risk": {"type": "boolean"},
    },
    "required": ["text", "lang", "changed_meaning_risk"],
}

PROMPT = """Turn the user's few words into ONE short, polite sentence to say on a phone call.
- Language: {call_lang}; script/style: {type_lang_description}.
- {gender_note}
- Keep the user's meaning exactly. Do not add facts, numbers, dates, names or requests they didn't give, except facts from CONTACT NOTES that the words clearly refer to (e.g. "my medicine" -> the medicine in the notes).
- If the words are ambiguous, still draft the most likely sentence and set changed_meaning_risk=true.
- Never include OTPs, PINs, card numbers or passwords.
- Max 25 words. Return JSON only.

LAST THING THEY SAID: {last_caption}
CONTACT NOTES: {contact_notes}
USER'S WORDS: {words}"""


class DraftOut(BaseModel):
    text: str = Field(min_length=1, max_length=240)
    lang: str = ""
    changed_meaning_risk: bool = False

    @field_validator("text")
    @classmethod
    def safe(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v or DIGIT_RUN.search(v):
            raise ValueError("unusable draft")
        return v


@dataclass
class Draft:
    text: str
    lang: str
    risk: bool


async def make_draft(
    llm: Llm,
    *,
    words: str,
    call_lang: str,
    type_lang: str,
    last_caption: str,
    contact_notes: str,
    gender: str = "unspecified",
) -> Draft | None:
    """One validated draft, one retry on bad output, otherwise None."""
    prompt = PROMPT.format(
        call_lang={"hi-IN": "Hindi", "mr-IN": "Marathi", "en-IN": "English"}.get(
            call_lang, "Hindi"
        ),
        type_lang_description=TYPE_LANG_DESCRIPTION.get(type_lang, "Hindi in English letters"),
        last_caption=last_caption or "(nothing yet)",
        contact_notes=contact_notes or "none",
        words=words,
        gender_note=gender_note(gender),
    )
    for _ in range(2):
        try:
            out = DraftOut.model_validate(await llm.complete_json(prompt, schema=SCHEMA))
        except (ValidationError, ValueError, KeyError):
            continue
        except Exception:  # noqa: BLE001 - provider down
            return None
        return Draft(out.text, out.lang, out.changed_meaning_risk)
    return None
