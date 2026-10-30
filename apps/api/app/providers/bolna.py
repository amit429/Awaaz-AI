"""Bolna API client: place and stop calls for agents."""

import logging
import re
from typing import Any

import httpx

from app.config import Settings

log = logging.getLogger("awaaz.bolna")


class BolnaError(Exception):
    """Bolna refused or failed a request; `message` is safe to show the user."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class BolnaClient:
    def __init__(self, settings: Settings) -> None:
        self.base = settings.bolna_api_base.rstrip("/")
        self.headers = {"Authorization": f"Bearer {settings.bolna_api_key}"}

    async def start_call(self, agent_id: str, to: str, user_data: dict[str, Any]) -> str:
        """Place the call; returns Bolna's execution id."""
        body = {"agent_id": agent_id, "recipient_phone_number": to, "user_data": user_data}
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{self.base}/call", json=body, headers=self.headers)
        if r.status_code != 200:
            try:
                message = r.json().get("message") or r.text[:200]
            except ValueError:
                message = r.text[:200]
            raise BolnaError(str(message))
        return str(r.json()["execution_id"])

    async def stop_call(self, execution_id: str) -> str:
        """Ask Bolna to hang up. Returns "stopped" when it accepted, otherwise Bolna's own status
        for the call from its refusal ("Cannot stop call with status: initiated"), or "error"."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(f"{self.base}/call/{execution_id}/stop", headers=self.headers)
        except httpx.HTTPError as exc:
            log.warning("stop call failed: %s", exc)
            return "error"
        if r.status_code == 200:
            log.info("stop call accepted")
            return "stopped"
        log.warning("stop call refused: %s %s", r.status_code, r.text[:120])
        hit = re.search(r"status:\s*([\w-]+)", r.text)
        return hit.group(1) if hit else "error"
