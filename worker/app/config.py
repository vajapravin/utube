"""Worker configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    REDIS_URL: str = "redis://redis:6380/0"
    DATABASE_URL: str = (
        "postgresql+asyncpg://mytube:mytube_secure_dev_password_change_in_prod@postgres_db:5432/mytube"
    )

    # YouTube API
    VIDEO_SOURCE: str = "youtube_data_api"
    YT_API_KEY: str = ""
    YT_DAILY_QUOTA_BUDGET: int = 9000
    YT_DEFAULT_REGION: str = "GB"
    SHORTS_MAX_SECONDS: int = 180
    SHORTS_STRICT_CHECK: bool = False

    # LLM
    LLM_PROVIDER: str = "gemini"
    LLM_MODEL: str = "gemini-2.5-flash"
    GEMINI_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    CURATION_MIN_SCORE: int = 60
    CHANNEL_MAX_VIDEOS: int = 60
    CHANNEL_MAX_SHORTS: int = 40
    CHANNEL_REFRESH_HOURS: int = 24
    CATEGORY_REFRESH_HOURS: int = 12


@lru_cache
def get_worker_settings() -> WorkerSettings:
    return WorkerSettings()
