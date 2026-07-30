"""Geo helpers (offline: haversine + transport estimate + no-postcode path)."""

import pytest

from app.integrations import geo

from .conftest import auth_header, login

pytestmark = pytest.mark.asyncio


def test_haversine_london_to_manchester():
    # London ~ (51.5074, -0.1278), Manchester ~ (53.4808, -2.2426): ~160 miles straight line.
    miles = geo.haversine_miles(51.5074, -0.1278, 53.4808, -2.2426)
    assert 150 < miles < 175


def test_haversine_zero_distance():
    assert geo.haversine_miles(52.0, -1.0, 52.0, -1.0) == 0


def test_estimate_transport_has_floor_and_scales():
    assert geo.estimate_transport(0) == pytest.approx(45.0)
    assert geo.estimate_transport(100) > geo.estimate_transport(10)


async def test_auction_transport_without_postcodes_returns_note(client, seeded):
    token = await login(client, "buyer@example.com")
    houses = await client.get("/api/v1/auction-houses", headers=auth_header(token))
    house_id = houses.json()[0]["id"]
    resp = await client.get(f"/api/v1/geo/auction-transport/{house_id}", headers=auth_header(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["miles"] is None
    assert "postcode" in body["note"].lower()
