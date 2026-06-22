from functools import lru_cache

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./local_jarvis.db"
    ollama_base_url: AnyHttpUrl = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    api_cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173"
    )
    jarvis_api_key: str = ""
    max_document_bytes: int = 2_000_000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
