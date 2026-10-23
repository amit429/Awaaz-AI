"""Local development only: mint a token so the app can be used without Supabase auth."""

import jwt
from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings

router = APIRouter(tags=["dev"])


@router.post("/v1/dev/token")
async def dev_token(
    payload: dict | None = None, settings: Settings = Depends(get_settings)
) -> dict:
    if settings.app_env != "local" or not settings.dev_jwt_secret:
        raise HTTPException(status_code=404)
    sub = str((payload or {}).get("sub") or "dev-user")
    token = jwt.encode(
        {"sub": sub, "aud": "authenticated"}, settings.dev_jwt_secret, algorithm="HS256"
    )
    return {"token": token, "user_id": sub}
