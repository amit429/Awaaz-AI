"""Supabase (PostgREST + Auth admin) implementation of the Store interface, using the service role."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from app.config import Settings
from app.store import IN_FLIGHT, Profile, ist_day_start

log = logging.getLogger("awaaz.store")


class SupabaseStore:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self.url = settings.supabase_url.rstrip("/")
        key = settings.supabase_service_role_key
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        self.client = client or httpx.AsyncClient(timeout=20)
        self._call_owner: dict[str, str] = {}  # call_id -> user_id (turns need it)
        self._bg: set[asyncio.Task[None]] = set()

    # ---------- helpers ----------
    async def _rest(
        self,
        method: str,
        table: str,
        *,
        params: dict | None = None,
        json: Any = None,
        prefer: str | None = None,
    ) -> Any:
        headers = dict(self.headers)
        if prefer:
            headers["Prefer"] = prefer
        r = await self.client.request(
            method, f"{self.url}/rest/v1/{table}", params=params, json=json, headers=headers
        )
        if r.status_code >= 400:
            raise RuntimeError(f"supabase {method} {table}: {r.status_code} {r.text[:200]}")
        return r.json() if r.content else None

    async def _admin_user(self, email: str) -> str:
        """Id of the auth user with this email, created (confirmed) if missing."""
        r = await self.client.post(
            f"{self.url}/auth/v1/admin/users",
            json={"email": email, "email_confirm": True},
            headers=self.headers,
        )
        if r.status_code in (200, 201):
            return str(r.json()["id"])
        page = 1
        while True:  # already exists: find it
            lst = await self.client.get(
                f"{self.url}/auth/v1/admin/users",
                params={"page": page, "per_page": 200},
                headers=self.headers,
            )
            users = lst.json().get("users", [])
            for u in users:
                if u.get("email") == email:
                    return str(u["id"])
            if len(users) < 200:
                raise RuntimeError(
                    f"could not create or find auth user {email}: {r.status_code} {r.text[:120]}"
                )
            page += 1

    # ---------- profiles ----------
    async def get_profile(self, user_id: str) -> Profile:
        prof, comm = await asyncio.gather(
            self._rest("GET", "profiles", params={"user_id": f"eq.{user_id}", "select": "*"}),
            self._rest("GET", "comm_profiles", params={"user_id": f"eq.{user_id}", "select": "*"}),
        )
        p = Profile(user_id=user_id)
        if prof:
            p.display_name = prof[0]["display_name"]
            p.phone = prof[0].get("phone_e164")
        if comm:
            c = comm[0]
            p.onboarded = True
            p.easy_font, p.speech_rate = (
                c.get("easy_font", False),
                float(c.get("speech_rate", 0.75)),
            )
            p.preset, p.talk_modes, p.hear_modes = (
                c.get("preset"),
                c.get("talk_modes"),
                c.get("hear_modes"),
            )
            p.read_lang, p.type_lang = (
                c.get("read_lang", p.read_lang),
                c.get("type_lang", p.type_lang),
            )
            p.app_lang = c.get("app_lang") or p.app_lang
            p.gender = c.get("gender") or p.gender
        return p

    async def put_profile(self, profile: Profile) -> None:
        await self._rest(
            "POST",
            "profiles",
            params={"on_conflict": "user_id"},
            json={"user_id": profile.user_id, "display_name": profile.display_name},
            prefer="resolution=merge-duplicates",
        )
        comm = {
            "user_id": profile.user_id,
            "preset": profile.preset,
            "read_lang": profile.read_lang,
            "type_lang": profile.type_lang,
            "app_lang": profile.app_lang,
            "gender": profile.gender,
            "easy_font": profile.easy_font,
            "speech_rate": profile.speech_rate,
        }
        if profile.talk_modes:
            comm["talk_modes"] = profile.talk_modes
        if profile.hear_modes:
            comm["hear_modes"] = profile.hear_modes
        await self._rest(
            "POST",
            "comm_profiles",
            params={"on_conflict": "user_id"},
            json=comm,
            prefer="resolution=merge-duplicates",
        )

    async def seconds_used_today(self, user_id: str) -> int:
        rows = await self._rest(
            "GET",
            "calls",
            params={
                "user_id": f"eq.{user_id}",
                "created_at": f"gte.{ist_day_start().isoformat()}",
                "select": "duration_s",
            },
        )
        return sum(int(r.get("duration_s") or 0) for r in rows)

    async def add_scam_event(
        self, call_id: str, turn_seq: int | None, reason: str, action: str
    ) -> None:
        row = {
            "call_id": call_id,
            "user_id": self._call_owner[call_id],
            "turn_seq": turn_seq,
            "reason": reason,
            "action": action,
        }
        try:
            await self._rest("POST", "scam_events", json=row)
        except Exception:
            log.exception("could not save a scam event")

    async def list_contacts(self, user_id: str) -> list[dict[str, Any]]:
        return await self._rest(
            "GET",
            "contacts",
            params={"user_id": f"eq.{user_id}", "select": "*", "order": "favourite.desc,name.asc"},
        )

    async def save_contact(
        self, user_id: str, data: dict[str, Any], contact_id: str | None = None
    ) -> dict[str, Any]:
        if contact_id:
            rows = await self._rest(
                "PATCH",
                "contacts",
                params={"id": f"eq.{contact_id}", "user_id": f"eq.{user_id}"},
                json=data,
                prefer="return=representation",
            )
            if not rows:
                raise KeyError(contact_id)
            return rows[0]
        rows = await self._rest(
            "POST",
            "contacts",
            params={"on_conflict": "user_id,phone_e164"},
            json={**data, "user_id": user_id},
            prefer="resolution=merge-duplicates,return=representation",
        )
        return rows[0]

    async def delete_contact(self, user_id: str, contact_id: str) -> None:
        await self._rest(
            "DELETE", "contacts", params={"id": f"eq.{contact_id}", "user_id": f"eq.{user_id}"}
        )

    async def list_phrases(self, user_id: str) -> list[dict[str, Any]]:
        return await self._rest(
            "GET",
            "phrases",
            params={"user_id": f"eq.{user_id}", "select": "*", "order": "created_at.asc"},
        )

    async def save_phrase(self, user_id: str, data: dict[str, Any]) -> dict[str, Any]:
        rows = await self._rest(
            "POST", "phrases", json={**data, "user_id": user_id}, prefer="return=representation"
        )
        return rows[0]

    async def delete_phrase(self, user_id: str, phrase_id: str) -> None:
        await self._rest(
            "DELETE", "phrases", params={"id": f"eq.{phrase_id}", "user_id": f"eq.{user_id}"}
        )

    async def dev_user(self, email: str = "dev@awaaz.local") -> str:
        return await self._admin_user(email)

    async def wa_user(self, wa_id: str, name: str | None) -> str:
        rows = await self._rest(
            "GET", "wa_users", params={"wa_id": f"eq.{wa_id}", "select": "user_id"}
        )
        if rows and rows[0].get("user_id"):
            user_id = rows[0]["user_id"]
        else:
            user_id = await self._admin_user(f"wa-{wa_id}@awaaz.local")
            await self._rest(
                "POST",
                "wa_users",
                params={"on_conflict": "wa_id"},
                json={"wa_id": wa_id, "user_id": user_id},
                prefer="resolution=merge-duplicates",
            )
        existing = await self.get_profile(user_id)
        if existing.display_name == "Friend" and name:
            existing.display_name = name
            await self.put_profile(existing)
        elif not await self._rest(
            "GET", "profiles", params={"user_id": f"eq.{user_id}", "select": "user_id"}
        ):
            await self.put_profile(existing)
        return user_id

    # ---------- calls and turns ----------
    async def create_call(self, call: dict[str, Any]) -> None:
        self._call_owner[call["id"]] = call["user_id"]
        await self._rest("POST", "calls", json=call)

    async def has_consent(self, user_id: str, kind: str = "terms") -> bool:
        rows = await self._rest(
            "GET",
            "consents",
            params={"user_id": f"eq.{user_id}", "kind": f"eq.{kind}", "select": "id", "limit": "1"},
        )
        return bool(rows)

    async def add_consent(
        self, user_id: str, kind: str, text: str, evidence: dict[str, Any]
    ) -> None:
        await self._rest(
            "POST",
            "consents",
            json={"user_id": user_id, "kind": kind, "text": text, "evidence": evidence},
        )

    async def set_phone(self, user_id: str, phone: str) -> None:
        """Save the user's own number without touching their name."""
        rows = await self._rest(
            "GET", "profiles", params={"user_id": f"eq.{user_id}", "select": "user_id"}
        )
        if rows:
            await self._rest(
                "PATCH", "profiles", params={"user_id": f"eq.{user_id}"}, json={"phone_e164": phone}
            )
        else:  # before onboarding there is no name yet; the real one replaces it at onboarding
            await self._rest(
                "POST",
                "profiles",
                json={"user_id": user_id, "display_name": "Friend", "phone_e164": phone},
            )

    async def get_summary(self, call_id: str) -> dict[str, Any] | None:
        rows = await self._rest(
            "GET", "summaries", params={"call_id": f"eq.{call_id}", "select": "summary"}
        )
        return rows[0]["summary"] if rows else None

    async def save_summary(self, call_id: str, user_id: str, summary: dict[str, Any]) -> None:
        await self._rest(
            "POST",
            "summaries",
            params={"on_conflict": "call_id"},
            json={"call_id": call_id, "user_id": user_id, "summary": summary},
            prefer="resolution=merge-duplicates",
        )

    async def update_call(self, call_id: str, **fields: Any) -> None:
        await self._rest("PATCH", "calls", params={"id": f"eq.{call_id}"}, json=fields)

    async def end_orphaned_calls(self) -> int:
        rows = await self._rest(
            "PATCH",
            "calls",
            params={"status": f"in.({','.join(IN_FLIGHT)})"},
            json={"status": "ended", "ended_at": datetime.now(UTC).isoformat()},
            prefer="return=representation",
        )
        return len(rows or [])

    async def add_turn(self, call_id: str, turn: dict[str, Any]) -> None:
        """Persist in the background: a slow database must never delay a live call."""
        row = {
            "call_id": call_id,
            "user_id": self._call_owner[call_id],
            "seq": turn["seq"],
            "speaker": turn["speaker"],
            "source": turn["source"],
            "text": turn["text"],
            "text_translated": turn.get("text_translated"),
            "lang": turn.get("lang"),
            "confidence": turn.get("confidence"),
            "entities": turn.get("entities", []),
            "t_ms": turn["t_ms"],
        }
        task = asyncio.create_task(self._insert_turn(row))
        self._bg.add(task)
        task.add_done_callback(self._bg.discard)

    async def _insert_turn(self, row: dict[str, Any]) -> None:
        try:
            await self._rest("POST", "turns", json=row)
        except Exception:
            log.exception("could not save a turn")

    async def get_call(self, call_id: str) -> dict[str, Any] | None:
        rows = await self._rest("GET", "calls", params={"id": f"eq.{call_id}", "select": "*"})
        return rows[0] if rows else None

    async def get_turns(self, call_id: str) -> list[dict[str, Any]]:
        return await self._rest(
            "GET", "turns", params={"call_id": f"eq.{call_id}", "select": "*", "order": "seq.asc"}
        )

    async def list_calls(self, user_id: str, limit: int = 30) -> list[dict[str, Any]]:
        return await self._rest(
            "GET",
            "calls",
            params={
                "user_id": f"eq.{user_id}",
                "select": "*",
                "order": "created_at.desc",
                "limit": str(limit),
            },
        )
