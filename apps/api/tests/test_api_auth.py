"""Auth and RBAC integration tests."""

import pytest

from .conftest import auth_header, login

pytestmark = pytest.mark.asyncio


async def test_login_success_and_me(client, seeded):
    token = await login(client, "admin@example.com")
    resp = await client.get("/api/v1/auth/me", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin@example.com"
    assert resp.json()["role"] == "ADMIN"


async def test_login_wrong_password(client, seeded):
    resp = await client.post("/api/v1/auth/login",
                             json={"email": "admin@example.com", "password": "wrong"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "http_401"


async def test_unauthenticated_is_rejected(client, seeded):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_viewer_cannot_create_vehicle(client, seeded):
    token = await login(client, "viewer@example.com")
    resp = await client.post("/api/v1/vehicles", headers=auth_header(token),
                             json={"make": "Ford", "model": "Focus"})
    assert resp.status_code == 403


async def test_buyer_can_create_vehicle(client, seeded):
    token = await login(client, "buyer@example.com")
    resp = await client.post("/api/v1/vehicles", headers=auth_header(token),
                             json={"make": "Ford", "model": "Focus", "registration": "AB19FGH"})
    assert resp.status_code == 201
    assert resp.json()["make"] == "Ford"


async def test_viewer_cannot_manage_users(client, seeded):
    token = await login(client, "viewer@example.com")
    resp = await client.get("/api/v1/users", headers=auth_header(token))
    assert resp.status_code == 403


async def test_refresh_rotates_token(client, seeded):
    await login(client, "admin@example.com")  # sets refresh cookie on the client
    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_invalid_registration_is_rejected(client, seeded):
    token = await login(client, "buyer@example.com")
    resp = await client.post("/api/v1/vehicles", headers=auth_header(token),
                             json={"make": "Ford", "model": "Focus", "vin": "III"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"
