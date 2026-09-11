"""Pytest fixtures and test configuration for backend testing."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app


class MockAsyncSession:
    """Mock asynchronous database session for unit testing."""

    async def execute(self, statement):
        class MockResult:
            def scalar(self):
                return 1

        return MockResult()

    async def commit(self):
        pass

    async def rollback(self):
        pass

    async def close(self):
        pass


async def override_get_db() -> AsyncGenerator[MockAsyncSession, None]:
    """Dependency override providing a mock session for testing without Postgres."""
    yield MockAsyncSession()


# Apply dependency override for isolated testing
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an asynchronous HTTP test client for FastAPI routes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
