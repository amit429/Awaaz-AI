import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def auth(client):
    token = client.post("/v1/dev/token", json={}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_new_user_has_not_consented_until_they_agree(client):
    h = auth(client)
    assert client.get("/v1/me", headers=h).json()["consented"] is False
    r = client.post("/v1/consent", headers=h, json={"version": "2026-10"})
    assert r.status_code == 201 and r.json()["consented"] is True


def test_phone_number_is_optional_and_must_be_e164(client):
    h = auth(client)
    assert (
        client.post("/v1/consent", headers=h, json={"version": "v", "phone": "98227"}).status_code
        == 422
    )
    r = client.post("/v1/consent", headers=h, json={"version": "v", "phone": "+919822790187"})
    assert r.status_code == 201 and r.json()["profile"]["phone"] == "+919822790187"


def test_agreeing_twice_records_one_consent(client):
    from app.store import get_store

    h = auth(client)
    client.post("/v1/consent", headers=h, json={"version": "v"})
    client.post("/v1/consent", headers=h, json={"version": "v"})
    assert len(get_store().consents) == 1
