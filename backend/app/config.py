from functools import lru_cache

from pydantic import AnyHttpUrl, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_KEY_VALUES: frozenset[str] = frozenset({"", "change-me-before-real-use"})

_LOCAL_HOSTNAMES: tuple[str, ...] = ("localhost", "127.0.0.1", "0.0.0.0")


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
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() == "development"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def _enforce_production_security(self) -> "Settings":
        if self.is_development:
            return self

        if self.jarvis_api_key in _INSECURE_KEY_VALUES:
            raise ValueError(
                "JARVIS_API_KEY must be explicitly set to a strong secret when "
                "APP_ENV is not 'development'. The application will not start without it."
            )

        for origin in self.cors_origins:
            if any(hostname in origin for hostname in _LOCAL_HOSTNAMES):
                raise ValueError(
                    f"CORS origin '{origin}' contains a local address. "
                    "Set API_CORS_ORIGINS to your actual production origins when "
                    "APP_ENV is not 'development'."
                )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
