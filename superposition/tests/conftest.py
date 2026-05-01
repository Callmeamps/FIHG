import os

# Set test API key before anything else loads
os.environ["API_KEY"] = "dev"

import pytest
import pytest_asyncio
import asyncio

# Ensure models are registered
import superposition.models  # noqa: F401

from superposition.db import engine, Base
from main import verify_api_key

# Bypass auth in all tests
@pytest.fixture(scope="session", autouse=True)
def bypass_auth():
    from main import app
    app.dependency_overrides[verify_api_key] = lambda: None
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Drop and recreate all tables before tests run.

    Ensures schema matches current model definitions (handles column additions
    to existing tables like Agent.created_at).
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Could drop tables here if desired


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()