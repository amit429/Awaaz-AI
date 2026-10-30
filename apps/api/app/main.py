import logging
import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import (
    bolna_llm,
    calls,
    dev_auth,
    dev_console,
    stt,
    twilio_voice,
    webhooks_bolna,
    webhooks_wa,
)
from app.routers import settings as settings_router


_SECRET = re.compile(r"((?:token|s)=)[^&\s\"']+")


class RedactSecrets(logging.Filter):
    """Sign-in tokens travel in WebSocket URLs (and the webhook secret in Bolna's): keep them out
    of the server logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        # uvicorn's access formatter unpacks record.args, so redact them in place.
        if isinstance(record.args, tuple):
            record.args = tuple(self._clean(a) for a in record.args)
        elif isinstance(record.msg, str):
            record.msg = self._clean(record.msg)
        return True

    @staticmethod
    def _clean(value: object) -> object:
        return _SECRET.sub(r"\1***", value) if isinstance(value, str) else value


def _log_app_events() -> None:
    """Show our own INFO logs (call status webhooks, stop attempts) in the server output: only
    uvicorn's loggers had a handler, so everything under awaaz.* was silently dropped."""
    app_log = logging.getLogger("awaaz")
    if not app_log.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        app_log.addHandler(handler)
        app_log.setLevel(logging.INFO)
        app_log.propagate = False


def create_app() -> FastAPI:
    _log_app_events()
    for name in ("uvicorn.access", "uvicorn.error"):
        if not any(isinstance(f, RedactSecrets) for f in logging.getLogger(name).filters):
            logging.getLogger(name).addFilter(RedactSecrets())
    settings = get_settings()
    app = FastAPI(title="Awaaz API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=settings.cors_origin_regex,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    app.include_router(twilio_voice.router)
    app.include_router(calls.router)
    app.include_router(stt.router)
    app.include_router(settings_router.router)
    app.include_router(dev_auth.router)
    app.include_router(webhooks_bolna.router)
    app.include_router(webhooks_wa.router)
    app.include_router(bolna_llm.router)
    app.include_router(dev_console.router)

    @app.get("/v1/health")
    async def health() -> dict[str, object]:
        return {"ok": True, "mock": settings.mock_providers}

    return app


app = create_app()
