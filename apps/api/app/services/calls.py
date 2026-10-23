"""Create a relay call (session + store rows). Shared by the app API and the WhatsApp bot."""

import uuid

from app.config import Settings
from app.providers.bolna import BolnaClient
from app.providers.gemini import GeminiLlm
from app.providers.mocks import FakeCallee
from app.relay import bolna_registry, registry
from app.relay.bolna_leg import BolnaLeg
from app.relay.disclosure import disclosure_line
from app.relay.legs import MockLeg
from app.relay.session import RelaySession
from app.services.profiles import resolve_modes
from app.services.say_prep import make_preparer
from app.store import Store


class CallError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status, self.detail = status, detail


async def create_relay_call(
    *,
    user_id: str,
    to: str,
    settings: Settings,
    store: Store,
    call_language: str | None = None,
    talk_modes: list[str] | None = None,
    hear_modes: list[str] | None = None,
    callee: str | None = None,
    source: str = "app",
) -> RelaySession:
    """Register a session (not yet dialled: the first listener starts it). Raises CallError."""
    use_mock = bool(settings.mock_providers or callee)
    if not use_mock and not (settings.bolna_api_key and settings.bolna_relay_agent_id):
        raise CallError(501, "live telephony is not configured")
    profile = await store.get_profile(user_id)
    modes = resolve_modes(
        request_talk=talk_modes,
        request_hear=hear_modes,
        profile_talk=profile.talk_modes,
        profile_hear=profile.hear_modes,
        preset=profile.preset,
    )
    call_lang = call_language or "hi-IN"
    call_id = str(uuid.uuid4())
    if use_mock:
        try:
            leg = MockLeg(FakeCallee.from_fixture(callee or "pharmacy"))
        except FileNotFoundError as exc:
            raise CallError(422, "unknown callee fixture") from exc
    else:
        leg = BolnaLeg(
            BolnaClient(settings),
            agent_id=settings.bolna_relay_agent_id,
            to=to,
            call_id=call_id,
            disclosure=disclosure_line(profile.preset, call_lang, profile.display_name),
        )
        bolna_registry.add(leg)
    await store.create_call(
        {
            "id": call_id,
            "user_id": user_id,
            "kind": "wa_relay" if source == "whatsapp" else "relay",
            "direction": "outbound",
            "other_number": to,
            "call_lang": call_lang,
            "talk_modes": modes.talk,
            "hear_modes": modes.hear,
            "status": "created",
            "provider": "mock" if use_mock else "bolna",
        }
    )

    def cleanup() -> None:
        registry.remove(call_id)
        bolna_registry.remove(call_id)

    session = RelaySession(
        call_id=call_id,
        user_id=user_id,
        store=store,
        name=profile.display_name,
        preset=profile.preset,
        call_lang=call_lang,
        modes=modes,
        leg=leg,
        max_seconds=settings.max_call_minutes * 60,
        prepare=make_preparer(settings, call_lang, GeminiLlm(settings)),
        on_end=cleanup,
    )
    registry.add(session)
    return session
