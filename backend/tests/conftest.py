"""Pytest fixtures and test configuration for backend testing."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints.submissions import get_redis_client
from app.db.base import Base
from app.db.session import get_db
from app.main import app

# Import all models to register with Base.metadata
from app.models.submission import Submission  # noqa: F401
from app.models.user import User  # noqa: F401

# In-memory SQLite async engine for tests
test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class MockTestRedis:
    """Mock Redis client for submission testing."""

    def __init__(self):
        self.lists = {}

    async def lpush(self, key: str, value: str) -> int:
        if key not in self.lists:
            self.lists[key] = []
        self.lists[key].insert(0, value)
        return len(self.lists[key])

    async def aclose(self):
        pass


mock_redis_instance = MockTestRedis()


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency override providing an async SQLite session."""
    async with TestingSessionLocal() as session:
        yield session


async def override_get_redis_client() -> AsyncGenerator[MockTestRedis, None]:
    """Dependency override providing mock Redis client."""
    yield mock_redis_instance


# Apply global overrides
app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_redis_client] = override_get_redis_client


@pytest.fixture(autouse=True)
async def setup_database():
    """Create tables before each test and drop them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session fixture for direct test manipulation."""
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an asynchronous HTTP test client for FastAPI routes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
