"""Shared test fixtures for TechPulse Social tests."""

import pytest


@pytest.fixture(autouse=True)
def _reset_database_state():
    """Reset in-memory database state between tests."""
    import src.database as db

    original_store = db._memory_store.copy()
    original_init = db._initialized
    original_container = db._container
    original_client = db._cosmos_client

    # Force in-memory mode
    db._initialized = True
    db._container = None
    db._cosmos_client = None
    db._memory_store = {}

    yield

    # Restore original state
    db._memory_store = original_store
    db._initialized = original_init
    db._container = original_container
    db._cosmos_client = original_client


@pytest.fixture
def mock_env(monkeypatch):
    """Helper to set environment variables for config tests."""

    def _set(**kwargs):
        for key, value in kwargs.items():
            monkeypatch.setenv(key, value)

    return _set


@pytest.fixture
def sample_chat_body() -> dict:
    """Return a valid chat request body for API tests."""
    return {
        "message": "Launch our new AI product",
        "platforms": ["linkedin", "x"],
        "content_type": "product_launch",
        "language": "en",
        "reasoning_effort": "medium",
        "reasoning_summary": "auto",
    }
