"""Auction listings with search, filters, sort and pagination."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.deps import CurrentUser, require_buyer
from ...db.session import get_db
from ...integrations.connectors.base import NormalizedListing
from ...models.catalogue import AuctionHouse, AuctionListing, Vehicle
from ...models.organisation import User
from ...schemas.catalogue import (
    AuctionListingCreate,
    AuctionListingOut,
    AuctionListingUpdate,
    QuickAddListing,
)
from ...schemas.common import Page
from ...services.ingestion import ingest
from ...services.listing_parser import parse_listing

router = APIRouter(prefix="/listings", tags=["listings"])

SORTABLE = {"guide_price": AuctionListing.guide_price,
            "auction_datetime": AuctionListing.auction_datetime,
            "id": AuctionListing.id}


@router.get("", response_model=Page[AuctionListingOut])
async def list_listings(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    auction_house_id: int | None = None,
    make: str | None = None,
    fuel: str | None = None,
    transmission: str | None = None,
    condition_grade: int | None = None,
    listing_status: str | None = None,
    min_guide: float | None = None,
    max_guide: float | None = None,
    sort: str = Query("id"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    stmt = (select(AuctionListing).join(Vehicle, Vehicle.id == AuctionListing.vehicle_id)
            .where(AuctionListing.dealership_id == user.dealership_id))
    if auction_house_id:
        stmt = stmt.where(AuctionListing.auction_house_id == auction_house_id)
    if make:
        stmt = stmt.where(Vehicle.make == make)
    if fuel:
        stmt = stmt.where(Vehicle.fuel_type == fuel)
    if transmission:
        stmt = stmt.where(Vehicle.transmission == transmission)
    if condition_grade:
        stmt = stmt.where(AuctionListing.condition_grade == condition_grade)
    if listing_status:
        stmt = stmt.where(AuctionListing.listing_status == listing_status)
    if min_guide is not None:
        stmt = stmt.where(AuctionListing.guide_price >= min_guide)
    if max_guide is not None:
        stmt = stmt.where(AuctionListing.guide_price <= max_guide)

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    col = SORTABLE.get(sort, AuctionListing.id)
    col = col.asc() if order == "asc" else col.desc()
    rows = (await db.execute(
        stmt.options(selectinload(AuctionListing.vehicle).selectinload(Vehicle.history),
                     selectinload(AuctionListing.auction_house).selectinload(
                         AuctionHouse.fee_bands))
        .order_by(col).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    return Page(items=rows, total=total, page=page, page_size=page_size)


@router.get("/{listing_id}", response_model=AuctionListingOut)
async def get_listing(listing_id: int, user: CurrentUser,
                     db: Annotated[AsyncSession, Depends(get_db)]):
    listing = (await db.execute(
        select(AuctionListing).options(
            selectinload(AuctionListing.vehicle).selectinload(Vehicle.history),
            selectinload(AuctionListing.auction_house).selectinload(AuctionHouse.fee_bands))
        .where(AuctionListing.id == listing_id,
               AuctionListing.dealership_id == user.dealership_id)
    )).scalar_one_or_none()
    if listing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not found")
    return listing


@router.post("", response_model=AuctionListingOut, status_code=status.HTTP_201_CREATED)
async def create_listing(
    payload: AuctionListingCreate,
    buyer: Annotated[User, Depends(require_buyer)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    vehicle = await db.get(Vehicle, payload.vehicle_id)
    if vehicle is None or vehicle.dealership_id != buyer.dealership_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehicle not found")
    listing = AuctionListing(dealership_id=buyer.dealership_id, **payload.model_dump())
    db.add(listing)
    await db.flush()
    return await get_listing(listing.id, buyer, db)


class ParseListingRequest(BaseModel):
    text: str = Field(min_length=5, max_length=8000)


@router.post("/parse")
async def parse_pasted_listing(
    payload: ParseListingRequest,
    buyer: Annotated[User, Depends(require_buyer)],
):
    """Extract structured vehicle/damage details from pasted listing text (Claude, or heuristic)."""
    return parse_listing(payload.text)


@router.post("/quick-add", response_model=AuctionListingOut, status_code=status.HTTP_201_CREATED)
async def quick_add(
    payload: QuickAddListing,
    buyer: Annotated[User, Depends(require_buyer)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Add a single watched lot in one step (auction house auto-created; deduped by lot)."""
    lot = payload.lot_number or f"WATCH-{int(datetime.now(timezone.utc).timestamp())}"
    nl = NormalizedListing(
        source="MANUAL", auction_house_name=(payload.auction_house or "SYNETIQ"), lot_number=lot,
        make=payload.make, model=payload.model, registration=payload.registration or None,
        derivative=payload.derivative or None, model_year=payload.model_year,
        mileage=payload.mileage, fuel_type=payload.fuel_type or None,
        transmission=payload.transmission or None, guide_price=payload.guide_price,
        category_marker=payload.category_marker or None,
        runner_status=payload.runner_status or "RUNNER", notes=payload.notes or None,
    )
    await ingest(db, buyer.dealership_id, [nl])
    house = (await db.execute(
        select(AuctionHouse).where(AuctionHouse.dealership_id == buyer.dealership_id,
                                   AuctionHouse.name == nl.auction_house_name)
    )).scalar_one()
    listing = (await db.execute(
        select(AuctionListing).where(AuctionListing.dealership_id == buyer.dealership_id,
                                     AuctionListing.auction_house_id == house.id,
                                     AuctionListing.lot_number == lot)
    )).scalar_one()
    return await get_listing(listing.id, buyer, db)


@router.patch("/{listing_id}", response_model=AuctionListingOut)
async def update_listing(
    listing_id: int,
    payload: AuctionListingUpdate,
    buyer: Annotated[User, Depends(require_buyer)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    listing = await db.get(AuctionListing, listing_id)
    if listing is None or listing.dealership_id != buyer.dealership_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(listing, key, value)
    await db.flush()
    return await get_listing(listing_id, buyer, db)
