"""Quick-add single lot tests."""

import pytest

from .conftest import auth_header, login

pytestmark = pytest.mark.asyncio


async def test_quick_add_creates_listing_and_house(client, seeded):
    token = await login(client, "buyer@example.com")
    resp = await client.post("/api/v1/listings/quick-add", headers=auth_header(token), json={
        "make": "Ford", "model": "Focus", "registration": "WA19TCH",
        "model_year": 2019, "mileage": 40000, "guide_price": "4200",
        "lot_number": "L555", "auction_house": "SYNETIQ", "category_marker": "N",
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["lot_number"] == "L555"
    assert body["vehicle"]["make"] == "Ford"
    assert body["auction_house"]["name"] == "SYNETIQ"


async def test_quick_add_is_deduped_by_lot(client, seeded):
    token = await login(client, "buyer@example.com")
    payload = {"make": "Kia", "model": "Ceed", "lot_number": "DUP1", "auction_house": "SYNETIQ"}
    a = await client.post("/api/v1/listings/quick-add", headers=auth_header(token), json=payload)
    b = await client.post("/api/v1/listings/quick-add", headers=auth_header(token), json=payload)
    assert a.json()["id"] == b.json()["id"]


async def test_viewer_cannot_quick_add(client, seeded):
    token = await login(client, "viewer@example.com")
    resp = await client.post("/api/v1/listings/quick-add", headers=auth_header(token),
                             json={"make": "Ford", "model": "Focus"})
    assert resp.status_code == 403
