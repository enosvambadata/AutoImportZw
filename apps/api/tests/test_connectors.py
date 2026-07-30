"""Data-connector + ingestion pipeline tests (demo connector; no credentials needed)."""

import pytest
from sqlalchemy import func, select

from app.integrations.connectors import connector_status, get_catalogue_connector
from app.integrations.connectors.providers import (
    AutoTraderConnector,
    CopartConnector,
    SynetiqConnector,
)
from app.models.catalogue import AuctionListing
from app.services.ingestion import ingest

from .conftest import auth_header, login

pytestmark = pytest.mark.asyncio


def test_real_connectors_report_unconfigured_without_env():
    assert CopartConnector().is_configured() is False
    assert SynetiqConnector().is_configured() is False
    assert AutoTraderConnector().is_configured() is False


def test_status_lists_all_connectors():
    rows = {r["name"]: r for r in connector_status()}
    assert set(["demo", "copart", "synetiq", "autotrader"]).issubset(rows)
    assert rows["demo"]["configured"] is True
    assert rows["copart"]["configured"] is False


async def test_ingest_is_idempotent(session_factory, seeded):
    connector = get_catalogue_connector("demo")
    listings = connector.fetch_listings()
    async with session_factory() as s:
        first = await ingest(s, seeded["dealership_id"], listings)
        await s.commit()
    assert first["listings_created"] == len(listings)
    assert first["vehicles_created"] == len(listings)

    # Re-running updates rather than duplicating.
    async with session_factory() as s:
        second = await ingest(s, seeded["dealership_id"], listings)
        await s.commit()
        total = (await s.execute(
            select(func.count()).select_from(AuctionListing)
            .where(AuctionListing.dealership_id == seeded["dealership_id"])
        )).scalar_one()
    assert second["listings_created"] == 0
    assert second["listings_updated"] == len(listings)
    assert total == len(listings)


async def test_sync_endpoint_requires_admin_and_ingests(client, seeded):
    # Viewer cannot sync.
    vtoken = await login(client, "viewer@example.com")
    denied = await client.post("/api/v1/connectors/demo/sync", headers=auth_header(vtoken))
    assert denied.status_code == 403

    admin = await login(client, "admin@example.com")
    resp = await client.post("/api/v1/connectors/demo/sync", headers=auth_header(admin))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["source"] == "DEMO"
    assert body["listings_created"] > 0

    # The ingested listings are now queryable through the normal listings API.
    listings = await client.get("/api/v1/listings", headers=auth_header(admin))
    assert listings.json()["total"] >= body["listings_created"]


async def test_sync_unknown_connector_404(client, seeded):
    admin = await login(client, "admin@example.com")
    resp = await client.post("/api/v1/connectors/nope/sync", headers=auth_header(admin))
    assert resp.status_code == 404


async def test_sync_unconfigured_real_connector_409(client, seeded):
    admin = await login(client, "admin@example.com")
    resp = await client.post("/api/v1/connectors/copart/sync", headers=auth_header(admin))
    assert resp.status_code == 409
