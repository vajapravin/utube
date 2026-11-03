"""Application configuration via Pydantic Settings."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Application
    APP_NAME: str = "mytube"
    APP_ENV: str = "development"
    PUBLIC_BASE_URL: str = "https://utube.vajapravin.me"
    APP_SECRET_KEY: str = "insecure-dev-secret-key-change-in-production-64-bytes-padding-here"

    # Host Ports
    WEB_PORT: int = 3005
    API_PORT: int = 8005
    POSTGRES_PORT: int = 5436
    REDIS_PORT: int = 6381
    MOCK_OIDC_PORT: int = 8087

    # Database & Redis
    DATABASE_URL: str = (
        "postgresql+asyncpg://mytube:mytube_secure_dev_password_change_in_prod@postgres:5432/mytube"
    )
    REDIS_URL: str = "redis://redis:6379/0"

    # Authentication & OIDC
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    ALLOWED_EMAILS: str = "vajapravin23@gmail.com"
    ALLOWED_DOMAINS: str = ""
    OPEN_REGISTRATION: bool = False
    OIDC_DISCOVERY_URL: str = "https://accounts.google.com/.well-known/openid-configuration"

    # Video Source
    VIDEO_SOURCE: str = "youtube_data_api"
    YT_API_KEY: str = ""
    YT_DAILY_QUOTA_BUDGET: int = 9000
    YT_DEFAULT_REGION: str = "GB"
    SHORTS_MAX_SECONDS: int = 180
    SHORTS_STRICT_CHECK: bool = False

    # LLM Configuration
    LLM_PROVIDER: str = "gemini"
    LLM_MODEL: str = "gemini-2.5-flash"
    GEMINI_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LLM_DAILY_CALLS_PER_USER: int = 50
    CURATION_MIN_SCORE: int = 60
    CHANNEL_MAX_VIDEOS: int = 60
    CHANNEL_MAX_SHORTS: int = 40
    CHANNEL_REFRESH_HOURS: int = 24
    CATEGORY_REFRESH_HOURS: int = 12

    # Storage & Backups
    DATA_ROOT: str = "/volume1/docker/mytube"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def allowed_email_list(self) -> List[str]:
        if not self.ALLOWED_EMAILS:
            return []
        return [e.strip().lower() for e in self.ALLOWED_EMAILS.split(",") if e.strip()]

    @property
    def allowed_domain_list(self) -> List[str]:
        if not self.ALLOWED_DOMAINS:
            return []
        return [d.strip().lower() for d in self.ALLOWED_DOMAINS.split(",") if d.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
