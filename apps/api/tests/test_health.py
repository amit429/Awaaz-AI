from fastapi.testclient import TestClient

from app.main import app


def test_health():
    r = TestClient(app).get("/v1/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_redaction_keeps_uvicorn_access_log_formattable():
    """The filter hid tokens by blanking record.args, which broke uvicorn's access formatter
    ("not enough values to unpack") on every redacted line."""
    import logging

    from uvicorn.logging import AccessFormatter

    from app.main import RedactSecrets

    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        1,
        '%s - "%s %s HTTP/%s" %d',
        ("1.2.3.4:0", "GET", "/v1/relay/abc?token=SECRETJWT&last_turn=0", "1.1", 200),
        None,
    )
    assert RedactSecrets().filter(record)
    out = AccessFormatter('%(client_addr)s - "%(request_line)s" %(status_code)s').format(record)
    assert "SECRETJWT" not in out and "token=***" in out and "200" in out
