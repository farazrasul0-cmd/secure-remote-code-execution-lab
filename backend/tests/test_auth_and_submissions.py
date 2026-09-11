"""Integration tests for User Authentication and Code Submission APIs."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_user_registration_and_login_flow(async_client: AsyncClient):
    """Verify registration, login (form and json), and authenticated me profile."""
    # 1. Register new student
    register_payload = {
        "email": "ada.lovelace@university.edu",
        "username": "ada_lovelace",
        "password": "SecurePassword123!",
        "role": "student",
    }
    reg_res = await async_client.post("/api/v1/auth/register", json=register_payload)
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert reg_data["email"] == "ada.lovelace@university.edu"
    assert reg_data["username"] == "ada_lovelace"
    assert reg_data["role"] == "student"
    assert "id" in reg_data

    # 2. Prevent duplicate email registration
    dup_res = await async_client.post("/api/v1/auth/register", json=register_payload)
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"].lower()

    # 3. Login via JSON body
    login_json_payload = {
        "username_or_email": "ada_lovelace",
        "password": "SecurePassword123!",
    }
    login_res = await async_client.post(
        "/api/v1/auth/login/json", json=login_json_payload
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    token = token_data["access_token"]

    # 4. Reject invalid password
    bad_login_res = await async_client.post(
        "/api/v1/auth/login/json",
        json={"username_or_email": "ada_lovelace", "password": "WrongPassword!"},
    )
    assert bad_login_res.status_code == 401

    # 5. Access /me profile
    headers = {"Authorization": f"Bearer {token}"}
    me_res = await async_client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["username"] == "ada_lovelace"


@pytest.mark.asyncio
async def test_code_submission_and_retrieval(async_client: AsyncClient):
    """Verify submission ingestion, list retrieval, and multi-tenant access boundaries."""
    # 1. Register and authenticate user A
    user_a = {
        "email": "turing@university.edu",
        "username": "alan_turing",
        "password": "TuringMachine2026!",
        "role": "student",
    }
    await async_client.post("/api/v1/auth/register", json=user_a)
    login_a = await async_client.post(
        "/api/v1/auth/login/json",
        json={"username_or_email": "alan_turing", "password": "TuringMachine2026!"},
    )
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Submit valid code payload
    sub_payload = {
        "source_code": "def compute():\n    return 42\nprint(compute())",
        "language": "python",
        "stdin_data": None,
    }
    sub_res = await async_client.post(
        "/api/v1/submissions",
        json=sub_payload,
        headers=headers_a,
    )
    assert sub_res.status_code == 202
    sub_data = sub_res.json()
    assert sub_data["status"] == "PENDING"
    assert sub_data["language"] == "python"
    assert "id" in sub_data
    submission_id = sub_data["id"]

    # 3. Reject unsupported language
    bad_lang_res = await async_client.post(
        "/api/v1/submissions",
        json={"source_code": "puts 'hello'", "language": "ruby"},
        headers=headers_a,
    )
    assert bad_lang_res.status_code == 400

    # 4. List user submissions
    list_res = await async_client.get("/api/v1/submissions", headers=headers_a)
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(item["id"] == submission_id for item in list_data["items"])

    # 5. Retrieve specific submission
    detail_res = await async_client.get(
        f"/api/v1/submissions/{submission_id}", headers=headers_a
    )
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == submission_id

    # 6. Verify multi-tenant isolation: user B cannot view user A's submission
    user_b = {
        "email": "hopper@university.edu",
        "username": "grace_hopper",
        "password": "CompilerPioneer1!",
        "role": "student",
    }
    await async_client.post("/api/v1/auth/register", json=user_b)
    login_b = await async_client.post(
        "/api/v1/auth/login/json",
        json={"username_or_email": "grace_hopper", "password": "CompilerPioneer1!"},
    )
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    denied_res = await async_client.get(
        f"/api/v1/submissions/{submission_id}", headers=headers_b
    )
    assert denied_res.status_code == 404
