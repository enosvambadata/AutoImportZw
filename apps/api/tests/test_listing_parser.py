"""Pasted-listing parsing (heuristic path — no Anthropic key needed)."""

import pytest

from app.services.listing_parser import parse_listing

from .conftest import auth_header, login

pytestmark = pytest.mark.asyncio

SAMPLE = (
    "Ford Focus 1.0 EcoBoost Titanium, 2018, 62,000 miles, Cat N, non-runner, guide £3,200. "
    "Diesel, Manual. Front end damage, airbags deployed, nearside wing scuffed."
)


def test_heuristic_extracts_core_fields():
    d = parse_listing(SAMPLE)
    assert d["source"] == "HEURISTIC"
    assert d["make"] == "Ford"
    assert d["model_year"] == 2018
    assert d["mileage"] == 62000
    assert d["category_marker"] == "N"
    assert d["runner_status"] == "NON_RUNNER"
    assert d["guide_price"] == 3200.0
    assert d["transmission"] == "Manual"


def test_heuristic_handles_sparse_text():
    d = parse_listing("Some random text with no vehicle details")
    assert d["make"] is None
    assert d["model_year"] is None
    assert d["runner_status"] == "UNKNOWN"


async def test_parse_endpoint(client, seeded):
    token = await login(client, "buyer@example.com")
    resp = await client.post("/api/v1/listings/parse", headers=auth_header(token),
                             json={"text": SAMPLE})
    assert resp.status_code == 200
    assert resp.json()["make"] == "Ford"
    assert resp.json()["mileage"] == 62000


async def test_parse_requires_text(client, seeded):
    token = await login(client, "buyer@example.com")
    resp = await client.post("/api/v1/listings/parse", headers=auth_header(token), json={"text": ""})
    assert resp.status_code == 422
