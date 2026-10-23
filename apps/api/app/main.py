from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import bolna_llm, dev_console, twilio_voice


def create_app() -> FastAPI:
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
    app.include_router(bolna_llm.router)
    app.include_router(dev_console.router)

    @app.get("/v1/health")
    async def health() -> dict[str, object]:
        return {"ok": True, "mock": settings.mock_providers}

    return app


app = create_app()
