"""Storefront: publish a car (admin) -> browse + enquire (public) -> admin sees the enquiry."""

import pytest

from .conftest import auth_header, login

pytestmark = pytest.mark.asyncio


async def _publish_car(client, token, *, status="PUBLISHED"):
    v = await client.post("/api/v1/vehicles", headers=auth_header(token),
                          json={"make": "Ford", "model": "Transit", "registration": "AB19FGH",
                                "model_year": 2016, "mileage": 90000})
    vehicle_id = v.json()["id"]
    resp = await client.post("/api/v1/storefront/listings", headers=auth_header(token), json={
        "vehicle_id": vehicle_id, "headline": "2016 Ford Transit vetted", "status": status,
        "currency": "USD", "vehicle_price": "6000", "ocean_freight": "1650", "import_duty": "2400",
        "service_fee": "700", "dest_city": "Harare", "dest_port": "Durban",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_publish_and_public_browse(client, seeded):
    token = await login(client, "buyer@example.com")
    listing = await _publish_car(client, token)
    slug = listing["slug"]
    assert slug.endswith(str(listing["id"]))

    # Public catalogue shows it, no auth.
    cars = await client.get("/api/public/cars")
    assert cars.status_code == 200
    assert any(c["slug"] == slug for c in cars.json())

    # Public detail carries the landed breakdown and total (6000+1650+2400+700 = 10750).
    detail = await client.get(f"/api/public/cars/{slug}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["landed"]["total"] in ("10750", "10750.00")
    assert body["make"] == "Ford"


async def test_draft_is_not_public(client, seeded):
    token = await login(client, "buyer@example.com")
    listing = await _publish_car(client, token, status="DRAFT")
    cars = await client.get("/api/public/cars")
    assert all(c["slug"] != listing["slug"] for c in cars.json())
    # Direct slug fetch for a DRAFT 404s publicly.
    assert (await client.get(f"/api/public/cars/{listing['slug']}")).status_code == 404


async def test_public_enquiry_reaches_admin(client, seeded):
    token = await login(client, "buyer@example.com")
    listing = await _publish_car(client, token)
    enq = await client.post("/api/public/enquiries",
                            json={"slug": listing["slug"], "name": "Tendai", "contact": "+263770000000",
                                  "message": "How much deposit?"})
    assert enq.status_code == 201
    admin = await client.get("/api/v1/storefront/enquiries", headers=auth_header(token))
    assert admin.status_code == 200
    assert any(e["name"] == "Tendai" for e in admin.json())


async def test_public_brief(client, seeded):
    token = await login(client, "buyer@example.com")
    resp = await client.post("/api/public/briefs",
                             json={"name": "Rui", "contact": "rui@example.com", "make": "Toyota",
                                   "model": "Hilux", "budget_usd": "15000"})
    assert resp.status_code == 201
    admin = await client.get("/api/v1/storefront/briefs", headers=auth_header(token))
    assert any(b["name"] == "Rui" for b in admin.json())
