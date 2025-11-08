# app/config.py
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # App
    APP_HOST: str = Field("0.0.0.0", description="Host to bind the app")
    APP_PORT: int = Field(8000, description="Port to run the app")
    ENV: str = Field("dev", description="Environment (dev|prod)")

    # Providers / modes
    ASR_MODE: str = Field("stub", description="asr mode: stub | local | cloud")
    LLM_MODE: str = Field("openai", description="llm mode: openai | local")
    TTS_MODE: str = Field("stub", description="tts mode: stub | local | cloud")

    # Provider keys / urls
    LLM_API_KEY: Optional[str] = Field(None, description="API key for LLM provider (if using cloud)")
    DB_URL: str = Field("sqlite:///./data/poc.db", description="Database URL")
    REDIS_URL: Optional[str] = Field(None, description="Redis URL (if used)")
    WEBHOOK_SECRET: str = Field("changeme", description="Secret to validate incoming webhooks")
    MEDIA_BASE_URL: str = Field("http://localhost:8000/media", description="Base URL for serving generated audio/media")

    # Logging / misc
    LOG_LEVEL: str = Field("info", description="Logging level")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Singleton settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Return a singleton Settings instance (loads from .env automatically).
    Use `get_settings()` instead of importing Settings() directly so other modules
    share the same instance.
    """
    global _settings
    if _settings is None:
        _settings = Settings()  # loads from environment / .env
    return _settings
