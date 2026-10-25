"""Request bodies for the settings API."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.events import Hear, Talk
from app.specs import load_json

Lang = Literal["hi", "mr", "en", "bn", "ta", "te", "kn", "ml", "gu", "pa", "or"]  # spoken
ReadLang = Literal["hi", "mr", "en", "bn", "ta", "te", "kn", "ml", "gu", "pa", "or", "hi-Latn"]


class ProfileIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=60)
    preset: str | None = None
    talk_modes: list[Talk] = Field(min_length=1)
    hear_modes: list[Hear] = Field(min_length=1)
    read_lang: ReadLang = "hi"
    type_lang: str = "hi-Latn"
    app_lang: ReadLang = "en"
    easy_font: bool = False
    speech_rate: float = Field(default=0.75, ge=0.5, le=1.2)

    @field_validator("preset")
    @classmethod
    def known_preset(cls, v: str | None) -> str | None:
        if v is not None and v not in load_json("data/presets.json"):
            raise ValueError("unknown preset")
        return v

    @field_validator("display_name")
    @classmethod
    def trimmed(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("name is empty")
        return v


class ContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    phone_e164: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
    call_lang: Lang | None = None
    notes: str | None = Field(default=None, max_length=500)
    favourite: bool = False
    talk_override: list[Talk] | None = None
    hear_override: list[Hear] | None = None


class PhraseIn(BaseModel):
    label: str = Field(min_length=1, max_length=60)
    text: str = Field(min_length=1, max_length=300)
    group_name: str | None = Field(default=None, max_length=40)
    contact_id: str | None = None


class ConsentIn(BaseModel):
    version: str = Field(min_length=1, max_length=20)
    phone: str | None = Field(default=None, pattern=r"^\+[1-9]\d{7,14}$")  # optional, E.164
