"""End-to-end API flow: appraisal -> preview -> purchase -> prep costs -> sale -> dashboard."""

from datetime import date

import pytest

from .conftest import auth_header, login

pytestmark = pytest.mark.asyncio


async def _make_vehicle_and_listing(client, token, house_id):
    v = await client.post("/api/v1/vehicles", headers=auth_header(token),
                          json={"make": "Ford", "model": "Focus", "registration": "AB19FGH",
                                "model_year": 2019, "mileage": 41000, "number_of_keys": 2})
    vehicle_id = v.json()["id"]
    listing = await client.post("/api/v1/listings", headers=auth_header(token),
                                json={"vehicle_id": vehicle_id, "auction_house_id": house_id,
                                      "guide_price": "5000", "condition_grade": 2,
                                      "runner_status": "RUNNER"})
    return vehicle_id, listing.json()["id"]


async def test_calculation_preview(client, seeded):
    token = await login(client, "buyer@example.com")
    resp = await client.post("/api/v1/appraisals/preview", headers=auth_header(token), json={
        "expected_retail_price": "9000", "conservative_retail_price": "8400",
        "optimistic_retail_price": "9500", "current_bid": "5000", "target_profit": "1200",
        "risk_reserve": "300", "desired_roi": "0.15",
        "cost_items": [{"name": "Service", "category": "SERVICE", "estimated_amount": "250",
                        "minimum_amount": "200", "maximum_amount": "350"}],
        "fee_bands": [{"percentage": "0.08", "minimum_fee": "180", "vat_applicable": True}],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["calculation"] is not None
    assert "safe_max_bid" in body["calculation"]
    assert body["recommendation"]["decision"] in {"STRONG_BUY", "BUY", "CONSIDER", "HIGH_RISK", "PASS"}
    assert body["recommendation"]["reasons"]


async def test_preview_incomplete_data(client, seeded):
    token = await login(client, "buyer@example.com")
    resp = await client.post("/api/v1/appraisals/preview", headers=auth_header(token),
                             json={"expected_retail_price": "9000"})
    assert resp.status_code == 200
    assert resp.json()["recommendation"]["decision"] == "INCOMPLETE_DATA"


async def test_full_purchase_to_sale_flow(client, seeded):
    token = await login(client, "buyer@example.com")
    _, listing_id = await _make_vehicle_and_listing(client, token, seeded["house_id"])
    vehicle_id = (await client.get(f"/api/v1/listings/{listing_id}",
                                   headers=auth_header(token))).json()["vehicle_id"]

    appr = await client.post("/api/v1/appraisals", headers=auth_header(token), json={
        "vehicle_id": vehicle_id, "auction_listing_id": listing_id,
        "expected_retail_price": "9000", "conservative_retail_price": "8400",
        "optimistic_retail_price": "9500", "current_bid": "5000",
        "cost_items": [{"name": "Service", "category": "SERVICE", "estimated_amount": "250",
                        "minimum_amount": "200", "maximum_amount": "350"}],
    })
    assert appr.status_code == 201, appr.text
    appraisal = appr.json()
    assert appraisal["safe_max_bid"] is not None
    assert appraisal["recommendation"] is not None
    appraisal_id = appraisal["id"]

    # Change a repair estimate -> results recalculate.
    updated = await client.put(f"/api/v1/appraisals/{appraisal_id}", headers=auth_header(token),
                               json={"expected_retail_price": "9000",
                                     "conservative_retail_price": "8400",
                                     "optimistic_retail_price": "9500", "current_bid": "5000",
                                     "cost_items": [{"name": "Big repair", "category": "MECHANICAL",
                                                     "estimated_amount": "1500",
                                                     "minimum_amount": "1000",
                                                     "maximum_amount": "2500"}]})
    assert updated.status_code == 200
    assert updated.json()["safe_max_bid"] != appraisal["safe_max_bid"]

    # Purchase requires explicit confirmation.
    unconf = await client.post("/api/v1/purchases", headers=auth_header(token),
                               json={"appraisal_id": appraisal_id, "actual_hammer_price": "5000",
                                     "purchase_date": str(date.today()), "confirm": False})
    assert unconf.status_code == 400

    purchase = await client.post("/api/v1/purchases", headers=auth_header(token),
                                 json={"appraisal_id": appraisal_id, "actual_hammer_price": "5000",
                                       "actual_auction_fees": "300", "actual_transport_cost": "180",
                                       "purchase_date": str(date.today()), "confirm": True})
    assert purchase.status_code == 201, purchase.text
    purchase_id = purchase.json()["id"]

    # Actual preparation costs.
    prepped = await client.post(f"/api/v1/purchases/{purchase_id}/preparation-costs",
                                headers=auth_header(token),
                                json={"category": "SERVICE", "description": "Full service",
                                      "actual_amount": "260"})
    assert prepped.status_code == 201
    assert prepped.json()["total_preparation_cost"] == "260.00"

    # Complete the sale -> actual profit computed.
    sale = await client.post("/api/v1/sales", headers=auth_header(token),
                             json={"purchase_id": purchase_id, "final_selling_price": "8800",
                                   "sale_date": str(date.today()), "warranty_cost": "180",
                                   "advertising_cost": "60", "finance_commission": "220"})
    assert sale.status_code == 201, sale.text
    body = sale.json()
    assert body["gross_profit"] is not None
    assert body["net_contribution"] is not None
    assert body["days_in_stock"] == 0

    # Dashboard reflects persisted data.
    dash = await client.get("/api/v1/analytics/dashboard", headers=auth_header(token))
    assert dash.status_code == 200
    assert dash.json()["vehicles_appraised"] >= 1
    assert dash.json()["average_actual_profit"] is not None


async def test_cannot_sell_before_purchase_date(client, seeded):
    token = await login(client, "buyer@example.com")
    _, listing_id = await _make_vehicle_and_listing(client, token, seeded["house_id"])
    vehicle_id = (await client.get(f"/api/v1/listings/{listing_id}",
                                   headers=auth_header(token))).json()["vehicle_id"]
    appr = await client.post("/api/v1/appraisals", headers=auth_header(token), json={
        "vehicle_id": vehicle_id, "expected_retail_price": "9000",
        "conservative_retail_price": "8400", "optimistic_retail_price": "9500",
        "current_bid": "5000"})
    purchase = await client.post("/api/v1/purchases", headers=auth_header(token),
                                 json={"appraisal_id": appr.json()["id"],
                                       "actual_hammer_price": "5000",
                                       "purchase_date": "2026-06-01", "confirm": True})
    sale = await client.post("/api/v1/sales", headers=auth_header(token),
                             json={"purchase_id": purchase.json()["id"],
                                   "final_selling_price": "8800", "sale_date": "2026-05-01"})
    assert sale.status_code == 422
