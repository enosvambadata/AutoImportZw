"""Photo damage-analysis tests (mock adapter path — no API key required)."""

import base64

import pytest

from app.integrations.vision import MockDamageAnalysisProvider

from .conftest import auth_header, login

pytestmark = pytest.mark.asyncio

# A 1x1 PNG.
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def test_mock_provider_returns_labelled_structured_result():
    provider = MockDamageAnalysisProvider()
    out = provider.analyse([("image/png", "x")], {"make": "Ford", "target_profit": "1200"})
    assert out["analysis_source"] == "MOCK_ADAPTER"
    assert "disclaimer" in out
    r = out["result"]
    assert r["overall_condition"] in {"EXCELLENT", "GOOD", "FAIR", "POOR"}
    assert isinstance(r["damage_items"], list) and r["damage_items"]
    assert isinstance(r["suggested_cost_items"], list) and r["suggested_cost_items"]
    assert r["recommended_checks"]


async def test_vision_status_reports_mock_when_no_key(client, seeded):
    token = await login(client, "buyer@example.com")
    resp = await client.get("/api/v1/vision/status", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["provider"] == "MOCK_ADAPTER"
    assert resp.json()["live"] is False


async def test_damage_endpoint_uses_mock_and_can_attach_costs(client, seeded):
    token = await login(client, "buyer@example.com")
    # Create a vehicle + appraisal to attach costs to.
    vehicle = await client.post("/api/v1/vehicles", headers=auth_header(token),
                                json={"make": "Ford", "model": "Focus", "model_year": 2019})
    appr = await client.post("/api/v1/appraisals", headers=auth_header(token), json={
        "vehicle_id": vehicle.json()["id"], "expected_retail_price": "9000",
        "conservative_retail_price": "8400", "optimistic_retail_price": "9500",
        "current_bid": "5000"})
    appraisal_id = appr.json()["id"]
    before = len(appr.json()["cost_items"])

    resp = await client.post(
        "/api/v1/vision/damage",
        headers=auth_header(token),
        files=[("files", ("car.png", PNG_1X1, "image/png"))],
        data={"appraisal_id": str(appraisal_id), "attach_costs": "true",
              "notes": "front end scuffed"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["analysis_source"] == "MOCK_ADAPTER"
    assert body["costs_attached"] is True

    # The appraisal now has more cost items and was recalculated.
    updated = await client.get(f"/api/v1/appraisals/{appraisal_id}", headers=auth_header(token))
    assert len(updated.json()["cost_items"]) > before


async def test_damage_endpoint_rejects_non_image(client, seeded):
    token = await login(client, "buyer@example.com")
    resp = await client.post(
        "/api/v1/vision/damage",
        headers=auth_header(token),
        files=[("files", ("notes.txt", b"hello", "text/plain"))],
    )
    assert resp.status_code == 422


async def test_viewer_cannot_analyse(client, seeded):
    token = await login(client, "viewer@example.com")
    resp = await client.post(
        "/api/v1/vision/damage",
        headers=auth_header(token),
        files=[("files", ("car.png", PNG_1X1, "image/png"))],
    )
    assert resp.status_code == 403
