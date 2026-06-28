import os
from pathlib import Path

import pytest

_TEST_DB = Path("test_jarvis.db")

# Remove any stale DB from a previous run.
if _TEST_DB.exists():
    _TEST_DB.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///./{_TEST_DB.name}"
os.environ["JARVIS_API_KEY"] = "test-key"

# Eagerly import the app so the engine is created with the URL above before any
# test module can override the environment variable.
from app.main import app  # noqa: F401


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Clean up the shared test database at the end of the session."""
    if _TEST_DB.exists():
        _TEST_DB.unlink()
