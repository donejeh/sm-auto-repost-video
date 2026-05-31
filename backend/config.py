"""Application configuration."""

from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT_DIR / ".env"), extra="ignore")

    app_secret_key: str = "dev-secret-change-in-production"
    app_env: str = "development"
    app_url: str = "http://localhost:5173"
    api_url: str = "http://localhost:8000"

    database_url: str = f"sqlite:///{ROOT_DIR / 'data' / 'autovideo.db'}"
    redis_url: str | None = None

    storage_path: Path = ROOT_DIR / "storage"
    log_dir: Path = ROOT_DIR / "logs"
    log_level: str = "INFO"
    max_upload_mb: int = 500

    session_lifetime_hours: int = 24

    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_redirect_uri: str = "http://localhost:8000/api/oauth/meta/callback"

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/oauth/google/callback"

    instagram_graph_access_token: str = ""
    instagram_business_account_id: str = ""
    facebook_page_id: str = ""

    ytdlp_cookies_file: str = "cookies-youtube.txt"
    instagram_cookies_file: str = "cookies-instagram.txt"

    # Anthropic-compatible API (optional — supports custom base URL proxies)
    anthropic_auth_token: str = ""
    anthropic_base_url: str = "https://api.anthropic.com"
    anthropic_default_sonnet_model: str = "claude-sonnet-4-6"
    openai_api_key: str = ""
    groq_api_key: str = ""

    token_encryption_key: str = ""

    @property
    def use_redis(self) -> bool:
        return bool(self.redis_url)

    @property
    def anthropic_configured(self) -> bool:
        return bool(self.anthropic_auth_token)

    @property
    def anthropic_messages_url(self) -> str:
        return f"{self.anthropic_base_url.rstrip('/')}/v1/messages"


@lru_cache
def get_settings() -> Settings:
    return Settings()
