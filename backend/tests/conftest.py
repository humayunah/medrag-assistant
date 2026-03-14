"""Shared test fixtures."""

import os

# Ensure test environment before anything else
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret-at-least-32-chars-long")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test.db")
os.environ.setdefault("HF_API_TOKEN", "test-hf-token")

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture
def client():
    """Synchronous test client — use for simple endpoint checks."""
    from fastapi.testclient import TestClient

    return TestClient(app)


@pytest.fixture
async def async_client():
    """Async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
