import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app import auth
from app.config import Settings, get_settings

SECRET = "s" * 40


def _token(secret=SECRET, aud="authenticated", sub="user-1"):
    return jwt.encode({"sub": sub, "aud": aud}, secret, algorithm="HS256")


def _client(secret: str) -> TestClient:
    app = FastAPI()
    app.dependency_overrides[get_settings] = lambda: Settings(supabase_jwt_secret=secret)

    @app.get("/me")
    async def me(uid: str = Depends(auth.current_user)):
        return {"uid": uid}

    return TestClient(app)


def test_valid_hs256_token():
    r = _client(SECRET).get("/me", headers={"Authorization": f"Bearer {_token()}"})
    assert r.status_code == 200 and r.json() == {"uid": "user-1"}


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer nonsense"}])
def test_missing_or_bad_token_is_401(headers):
    assert _client(SECRET).get("/me", headers=headers).status_code == 401


def test_wrong_secret_and_wrong_audience_rejected():
    c = _client(SECRET)
    assert c.get("/me", headers={"Authorization": f"Bearer {_token('x' * 40)}"}).status_code == 401
    assert (
        c.get("/me", headers={"Authorization": f"Bearer {_token(aud='anon')}"}).status_code == 401
    )


def test_hs256_rejected_when_no_secret_configured():
    r = _client("").get("/me", headers={"Authorization": f"Bearer {_token()}"})
    assert r.status_code == 401
