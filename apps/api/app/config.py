from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    public_base_url: str = "http://localhost:8000"
    web_base_url: str = "http://localhost:5173"
    cors_origins: str = "http://localhost:5173"
    cors_origin_regex: str = r"https://awaaz-.*\.vercel\.app"
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_jwks_url: str = ""
    supabase_jwt_secret: str = ""
    mock_providers: bool = True
    webhook_secret: str = "change-me-32-chars"
    max_call_minutes: int = 15
    daily_minutes_per_user: int = 60

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
