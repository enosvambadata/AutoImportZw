"""eBay parts sourcing (mock adapter path)."""

import pytest

from app.integrations.ebay import MockPartsProvider

from .conftest import auth_header, login

pytestmark = pytest.mark.asyncio


def test_mock_parts_returns_priced_items():
    items = MockPartsProvider().search("Ford Focus 2019 front bumper", limit=3)
    assert len(items) == 3
    assert all(i["price"] > 0 and i["currency"] == "GBP" for i in items)
    assert all(i["url"].startswith("https://www.ebay.co.uk/sch/") for i in items)


async def test_parts_for_damage_endpoint(client, seeded, monkeypatch):
    # Force the mock provider so the test never hits the network, regardless of local eBay keys.
    from app.api.v1 import parts as parts_module
    monkeypatch.setattr(parts_module, "get_parts_provider", lambda: MockPartsProvider())

    token = await login(client, "buyer@example.com")
    resp = await client.post("/api/v1/parts/for-damage", headers=auth_header(token), json={
        "make": "Ford", "model": "Focus", "model_year": 2019,
        "panels": ["Front bumper", "Alloy wheel"], "limit": 3,
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["provider"] == "MOCK_ADAPTER"
    assert len(body["groups"]) == 2
    assert "Front bumper" in body["groups"][0]["query"]
    assert body["groups"][0]["items"]


async def test_parts_requires_panels(client, seeded):
    token = await login(client, "buyer@example.com")
    resp = await client.post("/api/v1/parts/for-damage", headers=auth_header(token),
                             json={"make": "Ford", "model": "Focus", "panels": []})
    assert resp.status_code == 422


async def test_attach_parts_adds_costs_and_recomputes(client, seeded, monkeypatch):
    from app.api.v1 import parts as parts_module
    monkeypatch.setattr(parts_module, "get_parts_provider", lambda: MockPartsProvider())

    token = await login(client, "buyer@example.com")
    vehicle = await client.post("/api/v1/vehicles", headers=auth_header(token),
                                json={"make": "Ford", "model": "Focus", "model_year": 2019})
    appr = await client.post("/api/v1/appraisals", headers=auth_header(token), json={
        "vehicle_id": vehicle.json()["id"], "expected_retail_price": "9000",
        "conservative_retail_price": "8400", "optimistic_retail_price": "9500", "current_bid": "5000"})
    aid = appr.json()["id"]
    before = len(appr.json()["cost_items"])

    resp = await client.post(f"/api/v1/parts/attach/{aid}", headers=auth_header(token),
                             json={"panels": ["Front bumper", "Alloy wheel"]})
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["added"]) == 2
    assert resp.json()["recommendation"] in {"STRONG_BUY", "BUY", "CONSIDER", "HIGH_RISK", "PASS", "INCOMPLETE_DATA"}

    updated = await client.get(f"/api/v1/appraisals/{aid}", headers=auth_header(token))
    assert len(updated.json()["cost_items"]) == before + 2
    assert any("part (eBay)" in c["name"] for c in updated.json()["cost_items"])


async def test_viewer_cannot_search_parts(client, seeded):
    token = await login(client, "viewer@example.com")
    resp = await client.post("/api/v1/parts/for-damage", headers=auth_header(token),
                             json={"panels": ["Bumper"], "make": "Ford", "model": "Focus"})
    assert resp.status_code == 403
