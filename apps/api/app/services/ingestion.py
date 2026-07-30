"""Catalogue ingestion: upsert normalised connector listings into the database.

Idempotent — re-running a sync updates existing rows rather than duplicating them. After ingestion,
the whole platform (shortlist, appraisals, analytics) operates on these persisted rows, which is what
makes AutoBid a data-based system independent of the source.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..integrations.connectors.base import NormalizedListing
from ..models.catalogue import AuctionHouse, AuctionListing, Vehicle


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


async def _resolve_house(db: AsyncSession, dealership_id: int, name: str,
                        cache: dict[str, AuctionHouse]) -> AuctionHouse:
    if name in cache:
        return cache[name]
    house = (await db.execute(
        select(AuctionHouse).where(AuctionHouse.dealership_id == dealership_id,
                                   AuctionHouse.name == name)
    )).scalar_one_or_none()
    if house is None:
        house = AuctionHouse(dealership_id=dealership_id, name=name, fee_calc_type="PERCENTAGE")
        db.add(house)
        await db.flush()
    cache[name] = house
    return house


async def _resolve_vehicle(db: AsyncSession, dealership_id: int,
                          nl: NormalizedListing) -> tuple[Vehicle, bool]:
    vehicle = None
    if nl.registration:
        vehicle = (await db.execute(
            select(Vehicle).where(Vehicle.dealership_id == dealership_id,
                                  Vehicle.registration == nl.registration)
        )).scalar_one_or_none()
    if vehicle is None and nl.vin:
        vehicle = (await db.execute(
            select(Vehicle).where(Vehicle.dealership_id == dealership_id, Vehicle.vin == nl.vin)
        )).scalar_one_or_none()
    created = False
    if vehicle is None:
        vehicle = Vehicle(dealership_id=dealership_id, make=nl.make, model=nl.model)
        db.add(vehicle)
        created = True
    # Refresh identity/spec fields from the feed.
    vehicle.registration = nl.registration or vehicle.registration
    vehicle.vin = nl.vin or vehicle.vin
    vehicle.derivative = nl.derivative or vehicle.derivative
    vehicle.model_year = nl.model_year or vehicle.model_year
    vehicle.mileage = nl.mileage if nl.mileage is not None else vehicle.mileage
    vehicle.fuel_type = nl.fuel_type or vehicle.fuel_type
    vehicle.transmission = nl.transmission or vehicle.transmission
    vehicle.colour = nl.colour or vehicle.colour
    vehicle.category_marker = nl.category_marker or vehicle.category_marker
    vehicle.data_source = nl.source
    await db.flush()
    return vehicle, created


async def ingest(db: AsyncSession, dealership_id: int,
                listings: list[NormalizedListing]) -> dict[str, Any]:
    house_cache: dict[str, AuctionHouse] = {}
    created_vehicles = created_listings = updated_listings = 0

    for nl in listings:
        house = await _resolve_house(db, dealership_id, nl.auction_house_name, house_cache)
        vehicle, v_created = await _resolve_vehicle(db, dealership_id, nl)
        if v_created:
            created_vehicles += 1

        listing = (await db.execute(
            select(AuctionListing).where(
                AuctionListing.dealership_id == dealership_id,
                AuctionListing.auction_house_id == house.id,
                AuctionListing.lot_number == nl.lot_number)
        )).scalar_one_or_none()

        is_new = listing is None
        if is_new:
            listing = AuctionListing(dealership_id=dealership_id, vehicle_id=vehicle.id,
                                     auction_house_id=house.id, lot_number=nl.lot_number)
            db.add(listing)

        listing.vehicle_id = vehicle.id
        listing.auction_datetime = _parse_dt(nl.auction_datetime_iso) or listing.auction_datetime
        listing.guide_price = nl.guide_price if nl.guide_price is not None else listing.guide_price
        listing.cap_clean = nl.cap_clean if nl.cap_clean is not None else listing.cap_clean
        listing.cap_average = nl.cap_average if nl.cap_average is not None else listing.cap_average
        listing.cap_below = nl.cap_below if nl.cap_below is not None else listing.cap_below
        listing.estimated_retail = (nl.estimated_retail if nl.estimated_retail is not None
                                    else listing.estimated_retail)
        listing.condition_grade = nl.condition_grade or listing.condition_grade
        listing.runner_status = nl.runner_status or listing.runner_status
        listing.vat_status = nl.vat_status
        listing.direct_url = nl.direct_url or listing.direct_url
        listing.notes = nl.notes or listing.notes
        if nl.image_urls:
            listing.image_urls = nl.image_urls
        if nl.spin_urls:
            listing.spin_urls = nl.spin_urls
        listing.listing_status = "UPCOMING"
        listing.data_source = nl.source
        await db.flush()

        if is_new:
            created_listings += 1
        else:
            updated_listings += 1

    return {
        "ingested": len(listings),
        "vehicles_created": created_vehicles,
        "listings_created": created_listings,
        "listings_updated": updated_listings,
    }
