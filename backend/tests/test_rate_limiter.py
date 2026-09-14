"""Distributed rate limiter tests validating sliding window thresholds."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.conftest import mock_redis_instance


@pytest.mark.asyncio
async def test_rate_limiter_allows_requests_within_quota():
    """Verify that requests within the allowed rate limit threshold succeed."""
    mock_redis_instance.zsets.clear()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Register and login test user
        username = f"user_{uuid.uuid4().hex[:6]}"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"{username}@test.edu",
                "username": username,
                "password": "Password123!",
                "role": "student",
            },
        )
        login = await client.post(
            "/api/v1/auth/login/json",
            json={"username_or_email": username, "password": "Password123!"},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        for _ in range(3):
            response = await client.post(
                "/api/v1/submissions",
                headers=headers,
                json={"language": "python", "source_code": "print('ok')"},
            )
            assert response.status_code == 202


@pytest.mark.asyncio
async def test_rate_limiter_rejects_exceeded_quota_with_429():
    """Verify that exceeding the sliding window threshold returns HTTP 429."""
    mock_redis_instance.zsets.clear()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Register and login test user
        username = f"user_{uuid.uuid4().hex[:6]}"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"{username}@test.edu",
                "username": username,
                "password": "Password123!",
                "role": "student",
            },
        )
        login = await client.post(
            "/api/v1/auth/login/json",
            json={"username_or_email": username, "password": "Password123!"},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Default rate limit in config is 15/min. Dispatch 15 valid requests.
        for i in range(15):
            res = await client.post(
                "/api/v1/submissions",
                headers=headers,
                json={"language": "python", "source_code": f"print({i})"},
            )
            assert res.status_code == 202

        # 16th request breaches rate limit
        res_blocked = await client.post(
            "/api/v1/submissions",
            headers=headers,
            json={"language": "python", "source_code": "print('blocked')"},
        )
        assert res_blocked.status_code == 429
        assert "Rate limit exceeded" in res_blocked.json()["detail"]
        assert "Retry-After" in res_blocked.headers
