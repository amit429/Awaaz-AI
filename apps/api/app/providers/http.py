"""One long-lived HTTP client per provider and event loop, so calls reuse the connection instead
of paying for a new TLS handshake each time (about 0.2 s on every typed message)."""

import asyncio

import httpx

_clients: dict[tuple[str, int], httpx.AsyncClient] = {}


def shared(name: str, timeout: float) -> httpx.AsyncClient:
    """The shared client for `name` on the running event loop."""
    key = (name, id(asyncio.get_running_loop()))
    client = _clients.get(key)
    if client is None or client.is_closed:
        client = httpx.AsyncClient(
            timeout=timeout,
            limits=httpx.Limits(max_keepalive_connections=8, keepalive_expiry=60),
        )
        _clients[key] = client
    return client
