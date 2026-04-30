import pytest
import pytest_asyncio
import asyncio

# Ensure models are registered
import superposition.models  # noqa: F401

from superposition.db import engine, Base

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Create all tables once before tests run."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Could drop tables here if desired

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
