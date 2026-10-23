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


def test_dev_token_only_in_local_and_when_configured():
    from app.main import app

    def settings(**kw):
        return Settings(**kw)

    c = TestClient(app)
    app.dependency_overrides[get_settings] = lambda: settings(
        app_env="local", dev_jwt_secret="d" * 40
    )
    r = c.post("/v1/dev/token", json={"sub": "amit"})
    assert r.status_code == 200
    claims = jwt.decode(r.json()["token"], "d" * 40, algorithms=["HS256"], audience="authenticated")
    assert claims["sub"] == "amit"
    assert auth.verify_token(r.json()["token"], settings(app_env="local", dev_jwt_secret="d" * 40))
    app.dependency_overrides[get_settings] = lambda: settings(
        app_env="production", dev_jwt_secret="d" * 40
    )
    assert c.post("/v1/dev/token").status_code == 404
    with pytest.raises(jwt.PyJWTError):
        auth.verify_token(
            r.json()["token"], settings(app_env="production", dev_jwt_secret="d" * 40)
        )
    app.dependency_overrides.clear()
