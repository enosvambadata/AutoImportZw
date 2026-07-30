"""CSV import: SYNETIQ-style header mapping, preview, and commit-into-listings."""

import pytest

from app.services import csv_import

from .conftest import auth_header, login

pytestmark = pytest.mark.asyncio

# A SYNETIQ-style export using their likely column wording (mapped via aliases).
SYNETIQ_CSV = (
    "Reg,Make,Model,Derivative,Year,Mileage,Fuel,Gearbox,Lot No,Sale Date,Guide Price,"
    "Category,Starts & Drives,Location\n"
    "AB19XYZ,Ford,Focus,Titanium,2019,42000,Petrol,Manual,L901,2026-08-05T10:00,4200,Cat N,Runner,Doncaster\n"
    "CD18ABC,Vauxhall,Astra,SRi,2018,55000,Petrol,Manual,L902,2026-08-05T10:00,3100,,Non-Runner,Doncaster\n"
)


def test_synetiq_headers_map_to_canonical_fields():
    parsed = csv_import.parse_and_validate(SYNETIQ_CSV, profile="synetiq")
    assert parsed["summary"]["valid"] == 2
    first = parsed["rows"][0]["data"]
    assert first["make"] == "Ford"
    assert first["lot_number"] == "L901"       # "Lot No" -> lot_number
    assert first["guide_price"] == "4200"      # "Guide Price" -> guide_price
    # Category and runner status normalise on conversion.
    listings = csv_import.to_normalized_listings(parsed, profile="synetiq")
    assert listings[0].category_marker == "N"
    assert listings[0].runner_status == "RUNNER"
    assert listings[1].runner_status == "NON_RUNNER"
    assert listings[0].source == "SYNETIQ"
    assert listings[0].auction_house_name == "Doncaster"


async def test_commit_creates_listings_and_is_idempotent(client, seeded):
    token = await login(client, "buyer@example.com")

    def do_commit():
        return client.post(
            "/api/v1/imports/commit",
            headers=auth_header(token),
            files=[("file", ("synetiq.csv", SYNETIQ_CSV.encode(), "text/csv"))],
            data={"profile": "synetiq"},
        )

    first = await do_commit()
    assert first.status_code == 200, first.text
    assert first.json()["listings_created"] == 2
    assert first.json()["profile"] == "synetiq"

    # Imported listings appear through the normal listings API, labelled SYNETIQ.
    listings = await client.get("/api/v1/listings", headers=auth_header(token))
    makes = [l["vehicle"]["make"] for l in listings.json()["items"]]
    assert "Ford" in makes and "Vauxhall" in makes
    assert any(l["data_source"] == "SYNETIQ" for l in listings.json()["items"])

    # Re-importing updates rather than duplicating.
    second = await do_commit()
    assert second.json()["listings_created"] == 0
    assert second.json()["listings_updated"] == 2


async def test_preview_profile_flags_valid_rows(client, seeded):
    token = await login(client, "buyer@example.com")
    resp = await client.post(
        "/api/v1/imports/preview",
        headers=auth_header(token),
        files=[("file", ("synetiq.csv", SYNETIQ_CSV.encode(), "text/csv"))],
        data={"profile": "synetiq"},
    )
    assert resp.status_code == 200
    assert resp.json()["summary"]["valid"] == 2


async def test_commit_rejects_all_invalid(client, seeded):
    token = await login(client, "buyer@example.com")
    bad = "Make,Model\n,\n"  # missing required make/model
    resp = await client.post(
        "/api/v1/imports/commit",
        headers=auth_header(token),
        files=[("file", ("bad.csv", bad.encode(), "text/csv"))],
        data={"profile": "generic"},
    )
    assert resp.status_code == 422
