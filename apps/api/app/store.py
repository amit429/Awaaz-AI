"""Persistence boundary for calls and turns. InMemoryStore backs mock mode and tests; the
Supabase implementation (service role, REST) replaces it behind the same interface."""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from typing import Any, Protocol


def ist_day_start() -> datetime:
    """Midnight today in India (UTC+5:30), as an aware UTC datetime. Daily limits reset then."""
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)


@dataclass
class Profile:
    user_id: str
    display_name: str = "Friend"
    preset: str | None = None
    talk_modes: list[str] | None = None
    hear_modes: list[str] | None = None
    read_lang: str = "hi"
    type_lang: str = "hi-Latn"
    app_lang: str = "en"
    easy_font: bool = False
    speech_rate: float = 0.75
    onboarded: bool = False
    phone: str | None = None
    gender: str = "unspecified"  # male | female | unspecified: Hindi and Marathi verbs need it


IN_FLIGHT = ("created", "ringing", "connected")  # call statuses of a call that is still running


class Store(Protocol):
    async def get_profile(self, user_id: str) -> Profile: ...
    async def put_profile(self, profile: Profile) -> None: ...
    async def wa_user(self, wa_id: str, name: str | None) -> str: ...
    async def create_call(self, call: dict[str, Any]) -> None: ...
    async def update_call(self, call_id: str, **fields: Any) -> None: ...
    async def end_orphaned_calls(self) -> int:
        """Mark calls still shown as in progress as ended (sessions are in memory, so after a
        restart none of them is running). Returns how many were fixed."""
        ...

    async def add_turn(self, call_id: str, turn: dict[str, Any]) -> None: ...
    async def get_call(self, call_id: str) -> dict[str, Any] | None: ...
    async def get_turns(self, call_id: str) -> list[dict[str, Any]]: ...
    async def list_calls(self, user_id: str, limit: int = 30) -> list[dict[str, Any]]: ...
    async def list_contacts(self, user_id: str) -> list[dict[str, Any]]: ...
    async def save_contact(
        self, user_id: str, data: dict[str, Any], contact_id: str | None = None
    ) -> dict[str, Any]: ...
    async def delete_contact(self, user_id: str, contact_id: str) -> None: ...
    async def list_phrases(self, user_id: str) -> list[dict[str, Any]]: ...
    async def save_phrase(self, user_id: str, data: dict[str, Any]) -> dict[str, Any]: ...
    async def delete_phrase(self, user_id: str, phrase_id: str) -> None: ...
    async def seconds_used_today(self, user_id: str) -> int: ...
    async def add_scam_event(
        self, call_id: str, turn_seq: int | None, reason: str, action: str
    ) -> None: ...
    async def has_consent(self, user_id: str, kind: str = "terms") -> bool: ...
    async def add_consent(
        self, user_id: str, kind: str, text: str, evidence: dict[str, Any]
    ) -> None: ...
    async def set_phone(self, user_id: str, phone: str) -> None: ...
    async def get_summary(self, call_id: str) -> dict[str, Any] | None: ...
    async def save_summary(self, call_id: str, user_id: str, summary: dict[str, Any]) -> None: ...
    async def dev_user(self, email: str = "dev@awaaz.local") -> str: ...


@dataclass
class InMemoryStore:
    profiles: dict[str, Profile] = field(default_factory=dict)
    scam_events: list[dict[str, Any]] = field(default_factory=list)
    contacts: dict[str, dict[str, Any]] = field(default_factory=dict)
    phrases: dict[str, dict[str, Any]] = field(default_factory=dict)
    calls: dict[str, dict[str, Any]] = field(default_factory=dict)
    turns: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    summaries: dict[str, dict[str, Any]] = field(default_factory=dict)
    consents: list[dict[str, Any]] = field(default_factory=list)

    async def get_profile(self, user_id: str) -> Profile:
        return self.profiles.get(user_id) or Profile(user_id=user_id)

    async def put_profile(self, profile: Profile) -> None:
        profile.onboarded = True
        self.profiles[profile.user_id] = profile

    async def seconds_used_today(self, user_id: str) -> int:
        start = ist_day_start().isoformat()
        return sum(
            int(c.get("duration_s") or 0)
            for c in self.calls.values()
            if c["user_id"] == user_id and c["created_at"] >= start
        )

    async def add_scam_event(
        self, call_id: str, turn_seq: int | None, reason: str, action: str
    ) -> None:
        self.scam_events.append(
            {"call_id": call_id, "turn_seq": turn_seq, "reason": reason, "action": action}
        )

    async def list_contacts(self, user_id: str) -> list[dict[str, Any]]:
        mine = [c for c in self.contacts.values() if c["user_id"] == user_id]
        return sorted(mine, key=lambda c: (not c.get("favourite"), c["name"].lower()))

    async def save_contact(
        self, user_id: str, data: dict[str, Any], contact_id: str | None = None
    ) -> dict[str, Any]:
        if contact_id and (self.contacts.get(contact_id) or {}).get("user_id") != user_id:
            raise KeyError(contact_id)
        cid = contact_id or str(uuid.uuid4())
        row = {**self.contacts.get(cid, {}), **data, "id": cid, "user_id": user_id}
        self.contacts[cid] = row
        return row

    async def delete_contact(self, user_id: str, contact_id: str) -> None:
        if (self.contacts.get(contact_id) or {}).get("user_id") == user_id:
            del self.contacts[contact_id]

    async def list_phrases(self, user_id: str) -> list[dict[str, Any]]:
        return [p for p in self.phrases.values() if p["user_id"] == user_id]

    async def save_phrase(self, user_id: str, data: dict[str, Any]) -> dict[str, Any]:
        pid = str(uuid.uuid4())
        self.phrases[pid] = {**data, "id": pid, "user_id": user_id, "use_count": 0}
        return self.phrases[pid]

    async def delete_phrase(self, user_id: str, phrase_id: str) -> None:
        if (self.phrases.get(phrase_id) or {}).get("user_id") == user_id:
            del self.phrases[phrase_id]

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

    async def end_orphaned_calls(self) -> int:
        stuck = [c for c in self.calls.values() if c.get("status") in IN_FLIGHT]
        for call in stuck:
            call.update(status="ended", ended_at=datetime.now(UTC).isoformat())
        return len(stuck)

    async def add_turn(self, call_id: str, turn: dict[str, Any]) -> None:
        self.turns[call_id].append(turn)

    async def get_call(self, call_id: str) -> dict[str, Any] | None:
        return self.calls.get(call_id)

    async def get_turns(self, call_id: str) -> list[dict[str, Any]]:
        return list(self.turns.get(call_id, []))

    async def list_calls(self, user_id: str, limit: int = 30) -> list[dict[str, Any]]:
        mine = [c for c in self.calls.values() if c["user_id"] == user_id]
        return sorted(mine, key=lambda c: c["created_at"], reverse=True)[:limit]

    async def has_consent(self, user_id: str, kind: str = "terms") -> bool:
        return any(c["user_id"] == user_id and c["kind"] == kind for c in self.consents)

    async def add_consent(
        self, user_id: str, kind: str, text: str, evidence: dict[str, Any]
    ) -> None:
        self.consents.append({"user_id": user_id, "kind": kind, "text": text, "evidence": evidence})

    async def set_phone(self, user_id: str, phone: str) -> None:
        p = self.profiles.get(user_id) or Profile(user_id=user_id)
        p.phone = phone
        self.profiles[user_id] = p

    async def get_summary(self, call_id: str) -> dict[str, Any] | None:
        return self.summaries.get(call_id)

    async def save_summary(self, call_id: str, user_id: str, summary: dict[str, Any]) -> None:
        self.summaries[call_id] = summary

    async def dev_user(self, email: str = "dev@awaaz.local") -> str:
        return "dev-user"


_store: Store | None = None


def get_store() -> Store:
    """Supabase when configured and live; in-memory in mock mode (and always in tests, see conftest)."""
    global _store
    if _store is None:
        from app.config import get_settings

        settings = get_settings()
        if (
            settings.supabase_url
            and settings.supabase_service_role_key
            and not settings.mock_providers
        ):
            from app.supabase_store import SupabaseStore

            _store = SupabaseStore(settings)
        else:
            _store = InMemoryStore()
    return _store
