"""Shared pytest configuration.

Sets the test DATABASE_URL and imports the app *before* any test module runs,
so the SQLAlchemy engine (and its lru_cache'd settings) are created exactly once
for the entire test session.  This prevents test isolation issues caused by
individual test modules trying to set DATABASE_URL after the engine was already
initialised.
"""

import os
from pathlib import Path

_TEST_DB = Path("test_jarvis.db")

# Remove any stale DB from a previous run.
if _TEST_DB.exists():
    _TEST_DB.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///./{_TEST_DB.name}"
os.environ["JARVIS_API_KEY"] = "test-key"

# Eagerly import the app so the engine is created with the URL above before any
# test module can override the environment variable.
from app.main import app  # noqa: F401


def pytest_sessionfinish(session: object, exitstatus: object) -> None:
    """Clean up the shared test database at the end of the session."""
    if _TEST_DB.exists():
        _TEST_DB.unlink()
