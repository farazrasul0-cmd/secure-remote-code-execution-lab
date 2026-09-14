"""Pytest fixtures and test configuration for backend testing."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.redis import get_redis_client
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


class MockRedisPipeline:
    """Mock Redis pipeline supporting atomic ZSET operations."""

    def __init__(self, client: "MockTestRedis"):
        self.client = client
        self.commands: list[tuple[str, tuple]] = []

    def zremrangebyscore(self, key: str, min_score: float, max_score: float):
        self.commands.append(("zremrangebyscore", (key, min_score, max_score)))
        return self

    def zcard(self, key: str):
        self.commands.append(("zcard", (key,)))
        return self

    def zadd(self, key: str, mapping: dict[str, float]):
        self.commands.append(("zadd", (key, mapping)))
        return self

    def expire(self, key: str, ttl: int):
        self.commands.append(("expire", (key, ttl)))
        return self

    async def execute(self) -> list:
        results = []
        for cmd, args in self.commands:
            if cmd == "zremrangebyscore":
                key, min_s, max_s = args
                zset = self.client.zsets.setdefault(key, {})
                to_remove = [m for m, s in zset.items() if min_s <= s <= max_s]
                for m in to_remove:
                    del zset[m]
                results.append(len(to_remove))
            elif cmd == "zcard":
                (key,) = args
                results.append(len(self.client.zsets.get(key, {})))
            elif cmd == "zadd":
                key, mapping = args
                zset = self.client.zsets.setdefault(key, {})
                for m, s in mapping.items():
                    zset[m] = s
                results.append(len(mapping))
            elif cmd == "expire":
                results.append(True)
        self.commands.clear()
        return results


class MockTestRedis:
    """Mock Redis client for submission and rate limiter testing."""

    def __init__(self):
        self.lists: dict[str, list[str]] = {}
        self.zsets: dict[str, dict[str, float]] = {}

    def pipeline(self, transaction: bool = True) -> MockRedisPipeline:
        return MockRedisPipeline(self)

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
