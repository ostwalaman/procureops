from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ProcureOps Exception Agent"
    database_url: str = "sqlite:///./procureops.db"
    data_source: str = "demo"
    kaggle_row_limit: int = 30
    confidence_threshold: float = 0.75
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
