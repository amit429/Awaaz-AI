"""Supabase JWT verification: JWKS (asymmetric keys) with an optional HS256 secret fallback."""

import jwt
from fastapi import Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)
_jwks_clients: dict[str, jwt.PyJWKClient] = {}


def _jwks(url: str) -> jwt.PyJWKClient:
    if url not in _jwks_clients:
        _jwks_clients[url] = jwt.PyJWKClient(url, cache_keys=True)
    return _jwks_clients[url]


def verify_token(token: str, settings: Settings) -> dict:
    """Return the verified claims or raise jwt.PyJWTError."""
    header = jwt.get_unverified_header(token)
    alg = header.get("alg", "")
    if alg == "HS256":
        if not settings.supabase_jwt_secret:
            raise jwt.InvalidAlgorithmError("HS256 tokens are not accepted without a secret")
        return jwt.decode(
            token, settings.supabase_jwt_secret, algorithms=["HS256"], audience="authenticated"
        )
    if not settings.supabase_jwks_url:
        raise jwt.InvalidTokenError("SUPABASE_JWKS_URL is not set")
    key = _jwks(settings.supabase_jwks_url).get_signing_key_from_jwt(token).key
    return jwt.decode(token, key, algorithms=["ES256", "RS256"], audience="authenticated")


def _user_id(token: str | None, settings: Settings) -> str:
    if not token:
        raise HTTPException(status_code=401, detail="missing token")
    try:
        claims = verify_token(token, settings)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc
    return claims["sub"]


async def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> str:
    return _user_id(creds.credentials if creds else None, settings)


async def ws_user(
    token: str | None = Query(None), settings: Settings = Depends(get_settings)
) -> str:
    """For WebSockets, where browsers cannot set headers: ?token=<jwt>."""
    return _user_id(token, settings)
