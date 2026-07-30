"""Registration enrichment → vehicle history → risk."""

import pytest

from .conftest import auth_header, login

pytestmark = pytest.mark.asyncio


async def test_enrich_populates_history_and_recomputes(client, seeded):
    token = await login(client, "buyer@example.com")
    vehicle = await client.post("/api/v1/vehicles", headers=auth_header(token),
                                json={"make": "Ford", "model": "Focus", "registration": "EN19RCH"})
    vid = vehicle.json()["id"]
    appr = await client.post("/api/v1/appraisals", headers=auth_header(token), json={
        "vehicle_id": vid, "expected_retail_price": "9000",
        "conservative_retail_price": "8400", "optimistic_retail_price": "9500",
        "current_bid": "5000"})
    appraisal_id = appr.json()["id"]

    resp = await client.post(f"/api/v1/vehicles/{vid}/enrich", headers=auth_header(token))
    assert resp.status_code == 200, resp.text
    hist = resp.json()["history"]
    assert hist is not None
    assert isinstance(hist["mot_pass_count"], int)
    assert isinstance(hist["dangerous_defect_count"], int)

    # The appraisal was recomputed and still carries a risk level.
    got = await client.get(f"/api/v1/appraisals/{appraisal_id}", headers=auth_header(token))
    assert got.json()["risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


async def test_enrich_without_registration_is_422(client, seeded):
    token = await login(client, "buyer@example.com")
    vehicle = await client.post("/api/v1/vehicles", headers=auth_header(token),
                                json={"make": "Ford", "model": "Focus"})
    resp = await client.post(f"/api/v1/vehicles/{vehicle.json()['id']}/enrich",
                             headers=auth_header(token))
    assert resp.status_code == 422


async def test_viewer_cannot_enrich(client, seeded):
    admin = await login(client, "buyer@example.com")
    vehicle = await client.post("/api/v1/vehicles", headers=auth_header(admin),
                                json={"make": "Ford", "model": "Focus", "registration": "VW19ABC"})
    vid = vehicle.json()["id"]
    viewer = await login(client, "viewer@example.com")
    resp = await client.post(f"/api/v1/vehicles/{vid}/enrich", headers=auth_header(viewer))
    assert resp.status_code == 403
