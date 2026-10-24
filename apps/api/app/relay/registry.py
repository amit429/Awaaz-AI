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


def active_for(user_id: str) -> RelaySession | None:
    """The user's call in progress, if any (one live call per user)."""
    return next((s for s in _sessions.values() if s.user_id == user_id and not s.ended), None)
