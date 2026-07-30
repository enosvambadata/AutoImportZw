"""Scan-and-shortlist tests: ranking, due-date filter and endpoint."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.catalogue import AuctionListing, Vehicle

from .conftest import auth_header, login

pytestmark = pytest.mark.asyncio


async def _seed_listing(engine, house_id, *, make, when, estimated_retail, guide, grade=2):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        vehicle = Vehicle(dealership_id=1, make=make, model="Model", model_year=2019,
                          mileage=40000, number_of_keys=2)
        s.add(vehicle)
        await s.flush()
        listing = AuctionListing(
            dealership_id=1, vehicle_id=vehicle.id, auction_house_id=house_id,
            lot_number="L1", auction_datetime=when, guide_price=guide,
            cap_average=str(int(estimated_retail * 0.9)), estimated_retail=str(estimated_retail),
            cap_clean=str(int(estimated_retail * 0.97)), condition_grade=grade,
            runner_status="RUNNER", listing_status="UPCOMING",
        )
        s.add(listing)
        await s.commit()


async def test_shortlist_ranks_profitable_cars(client, seeded, engine):
    # A car with strong headroom (low guide vs retail) should be shortlisted.
    await _seed_listing(engine, seeded["house_id"], make="Ford",
                        when=datetime.now(timezone.utc) + timedelta(days=1),
                        estimated_retail=9000, guide=4500)
    token = await login(client, "buyer@example.com")
    resp = await client.get("/api/v1/shortlist", headers=auth_header(token),
                            params={"include": "STRONG_BUY,BUY,CONSIDER"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["scanned"] >= 1
    assert any(c["make"] == "Ford" for c in body["candidates"])
    for c in body["candidates"]:
        assert c["decision"] in {"STRONG_BUY", "BUY", "CONSIDER"}
        assert c["estimate_source"] == "AUTOMATED_ESTIMATE"


async def test_due_today_filters_by_auction_date(client, seeded, engine):
    today = datetime.now(timezone.utc)
    await _seed_listing(engine, seeded["house_id"], make="Today",
                        when=today, estimated_retail=9000, guide=4500)
    await _seed_listing(engine, seeded["house_id"], make="Nextweek",
                        when=today + timedelta(days=7), estimated_retail=9000, guide=4500)
    token = await login(client, "buyer@example.com")
    resp = await client.get("/api/v1/shortlist", headers=auth_header(token),
                            params={"due_today": "true", "include": "STRONG_BUY,BUY,CONSIDER"})
    assert resp.status_code == 200
    makes = [c["make"] for c in resp.json()["candidates"]]
    assert "Today" in makes
    assert "Nextweek" not in makes


async def test_shortlist_requires_auth(client, seeded):
    resp = await client.get("/api/v1/shortlist")
    assert resp.status_code == 401
