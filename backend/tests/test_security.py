"""Tests for production security controls."""

import logging
import re

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.main import _SanitizingFilter


# ---------------------------------------------------------------------------
# Settings validation
# ---------------------------------------------------------------------------


def _make_settings(**overrides: str) -> Settings:
    """Create a Settings instance bypassing .env file and lru_cache."""
    defaults = {
        "database_url": "sqlite:///./test.db",
        "api_cors_origins": "http://localhost:5173",
    }
    defaults.update(overrides)
    return Settings.model_validate(defaults)


def test_development_allows_empty_api_key() -> None:
    settings = _make_settings(app_env="development", jarvis_api_key="")
    assert settings.jarvis_api_key == ""


def test_development_allows_insecure_default_key() -> None:
    settings = _make_settings(app_env="development", jarvis_api_key="change-me-before-real-use")
    assert settings.jarvis_api_key == "change-me-before-real-use"


def test_production_requires_api_key() -> None:
    with pytest.raises(ValidationError, match="JARVIS_API_KEY must be explicitly set"):
        _make_settings(
            app_env="production",
            jarvis_api_key="",
            api_cors_origins="https://app.example.com",
        )


def test_production_rejects_default_api_key() -> None:
    with pytest.raises(ValidationError, match="JARVIS_API_KEY must be explicitly set"):
        _make_settings(
            app_env="production",
            jarvis_api_key="change-me-before-real-use",
            api_cors_origins="https://app.example.com",
        )


def test_production_accepts_strong_api_key() -> None:
    settings = _make_settings(
        app_env="production",
        jarvis_api_key="s3cur3-rand0m-key-abc123",
        api_cors_origins="https://app.example.com",
    )
    assert settings.jarvis_api_key == "s3cur3-rand0m-key-abc123"


def test_production_rejects_localhost_cors_origin() -> None:
    with pytest.raises(ValidationError, match="local address"):
        _make_settings(
            app_env="production",
            jarvis_api_key="s3cur3-rand0m-key-abc123",
            api_cors_origins="http://localhost:5173",
        )


def test_production_rejects_127_cors_origin() -> None:
    with pytest.raises(ValidationError, match="local address"):
        _make_settings(
            app_env="production",
            jarvis_api_key="s3cur3-rand0m-key-abc123",
            api_cors_origins="http://127.0.0.1:5173",
        )


def test_production_accepts_remote_cors_origins() -> None:
    settings = _make_settings(
        app_env="production",
        jarvis_api_key="s3cur3-rand0m-key-abc123",
        api_cors_origins="https://app.example.com,https://other.example.com",
    )
    assert settings.cors_origins == ["https://app.example.com", "https://other.example.com"]


# ---------------------------------------------------------------------------
# Sanitizing log filter
# ---------------------------------------------------------------------------


def _make_record(msg: str) -> logging.LogRecord:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=msg,
        args=(),
        exc_info=None,
    )
    return record


def _apply_filter(msg: str) -> str:
    f = _SanitizingFilter()
    record = _make_record(msg)
    f.filter(record)
    return str(record.msg)


def test_filter_redacts_x_api_key_header() -> None:
    result = _apply_filter("Request headers: x-api-key: super-secret-value")
    assert "super-secret-value" not in result
    assert "[REDACTED]" in result


def test_filter_redacts_authorization_header() -> None:
    result = _apply_filter("Authorization: my-token-here")
    assert "my-token-here" not in result
    assert "[REDACTED]" in result


def test_filter_redacts_jarvis_api_key_env() -> None:
    result = _apply_filter("Loaded JARVIS_API_KEY=hunter2")
    assert "hunter2" not in result
    assert "[REDACTED]" in result


def test_filter_preserves_non_sensitive_messages() -> None:
    msg = "User submitted a new task: buy milk"
    result = _apply_filter(msg)
    assert result == msg


def test_filter_handles_args_tuple() -> None:
    f = _SanitizingFilter()
    record = _make_record("key=%s status=%d")
    record.args = ("x-api-key: abc123", 200)
    f.filter(record)
    sanitized_str_arg = record.args[0]  # type: ignore[index]
    int_arg = record.args[1]  # type: ignore[index]
    assert "abc123" not in sanitized_str_arg
    assert "[REDACTED]" in sanitized_str_arg
    assert int_arg == 200
