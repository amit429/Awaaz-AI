"""Active relay sessions by id (in memory; one API instance)."""

from app.relay.session import RelaySession

_sessions: dict[str, RelaySession] = {}


def add(session: RelaySession) -> None:
    _sessions[session.call_id] = session


def get(call_id: str) -> RelaySession | None:
    return _sessions.get(call_id)


def remove(call_id: str) -> None:
    _sessions.pop(call_id, None)


def clear() -> None:
    _sessions.clear()
