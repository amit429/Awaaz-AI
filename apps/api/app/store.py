"""Persistence boundary for calls and turns. InMemoryStore backs mock mode and tests; the
Supabase implementation (service role, REST) replaces it behind the same interface."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol


@dataclass
class Profile:
    user_id: str
    display_name: str = "Friend"
    preset: str | None = None
    talk_modes: list[str] | None = None
    hear_modes: list[str] | None = None
    read_lang: str = "hi"
    type_lang: str = "hi-Latn"


class Store(Protocol):
    async def get_profile(self, user_id: str) -> Profile: ...
    async def put_profile(self, profile: Profile) -> None: ...
    async def wa_user(self, wa_id: str, name: str | None) -> str: ...
    async def create_call(self, call: dict[str, Any]) -> None: ...
    async def update_call(self, call_id: str, **fields: Any) -> None: ...
    async def add_turn(self, call_id: str, turn: dict[str, Any]) -> None: ...
    async def get_call(self, call_id: str) -> dict[str, Any] | None: ...
    async def get_turns(self, call_id: str) -> list[dict[str, Any]]: ...


@dataclass
class InMemoryStore:
    profiles: dict[str, Profile] = field(default_factory=dict)
    calls: dict[str, dict[str, Any]] = field(default_factory=dict)
    turns: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    async def get_profile(self, user_id: str) -> Profile:
        return self.profiles.get(user_id) or Profile(user_id=user_id)

    async def put_profile(self, profile: Profile) -> None:
        self.profiles[profile.user_id] = profile

    async def wa_user(self, wa_id: str, name: str | None) -> str:
        """The user for a WhatsApp number (created on first contact, WhatsApp-only)."""
        user_id = f"wa-{wa_id}"
        if user_id not in self.profiles:
            self.profiles[user_id] = Profile(user_id=user_id, display_name=name or "Friend")
        elif name and self.profiles[user_id].display_name == "Friend":
            self.profiles[user_id].display_name = name
        return user_id

    async def create_call(self, call: dict[str, Any]) -> None:
        self.calls[call["id"]] = {**call, "created_at": datetime.now(UTC).isoformat()}
        self.turns[call["id"]] = []

    async def update_call(self, call_id: str, **fields: Any) -> None:
        self.calls[call_id].update(fields)

    async def add_turn(self, call_id: str, turn: dict[str, Any]) -> None:
        self.turns[call_id].append(turn)

    async def get_call(self, call_id: str) -> dict[str, Any] | None:
        return self.calls.get(call_id)

    async def get_turns(self, call_id: str) -> list[dict[str, Any]]:
        return list(self.turns.get(call_id, []))


_store: Store = InMemoryStore()


def get_store() -> Store:
    return _store
