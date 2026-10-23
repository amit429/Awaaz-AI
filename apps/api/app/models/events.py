"""Inbound relay events (app to server), validated with Pydantic. Matches
specs/protocol/relay-events.schema.json; outbound events are built in relay/session.py and
checked against the JSON Schema in the contract tests."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter

Talk = Literal["voice", "type", "replies", "help", "clarity", "sign"]
Hear = Literal["captions", "clear", "audio", "summary", "vibe", "translate"]


class UserTyping(BaseModel):
    t: Literal["user.typing"]


class UserSay(BaseModel):
    t: Literal["user.say"]
    text: str = Field(min_length=1, max_length=500)
    source: Literal["typed", "reply", "phrase", "draft"]
    preview_id: str | None = None


class SayConfirm(BaseModel):
    t: Literal["say.confirm"]
    preview_id: str


class DraftRequest(BaseModel):
    t: Literal["draft.request"]
    words: str = Field(min_length=1, max_length=200)


class AskRepeat(BaseModel):
    t: Literal["user.ask_repeat"]


class Respeak(BaseModel):
    t: Literal["user.respeak"]
    turn: int | None = None
    rate: float | None = Field(default=None, ge=0.5, le=1.2)


class Dtmf(BaseModel):
    t: Literal["user.dtmf"]
    digits: str = Field(pattern=r"^[0-9*#]{1,20}$")


class ModeSet(BaseModel):
    t: Literal["mode.set"]
    talk_modes: list[Talk] | None = None
    hear_modes: list[Hear] | None = None


class CallEnd(BaseModel):
    t: Literal["call.end"]


class Ping(BaseModel):
    t: Literal["ping"]


ClientEvent = Annotated[
    UserTyping
    | UserSay
    | SayConfirm
    | DraftRequest
    | AskRepeat
    | Respeak
    | Dtmf
    | ModeSet
    | CallEnd
    | Ping,
    Field(discriminator="t"),
]
client_event = TypeAdapter(ClientEvent)
