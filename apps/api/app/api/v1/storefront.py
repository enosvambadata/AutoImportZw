"""Admin storefront management: publish appraised cars as candidates, review enquiries and briefs."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.deps import CurrentUser, require_buyer
from ...db.session import get_db
from ...models.catalogue import Vehicle
from ...models.organisation import User
from ...models.storefront import BuyerBrief, Enquiry, SaleListing
from ...schemas.storefront import (
    BuyerBriefOut,
    DutyQuoteOut,
    DutyQuoteRequest,
    EnquiryOut,
    SaleListingAdminOut,
    SaleListingCreate,
    SaleListingUpdate,
)
from ...services.image_processing import blur_background
from ...services.landed_cost import list_categories, zim_duty

router = APIRouter(prefix="/storefront", tags=["storefront-admin"])

_SOLD_STATES = {"SHIPPED", "DELIVERED"}

# Uploaded photos go to the API media dir (a persistent volume in prod), served at /media/cars/<key>/.
_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
_MAX_BYTES = 8 * 1024 * 1024
_MAX_FILES = 24


def _slugify(text: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return text[:120] or "car"


@router.post("/upload")
async def upload_images(
    buyer: Annotated[User, Depends(require_buyer)],
    key: Annotated[str, Form()],
    files: list[UploadFile] = File(...),
):
    """Save vehicle photos to the public storefront folder; returns their URLs to store on a listing."""
    safe = re.sub(r"[^a-z0-9-]+", "-", key.lower()).strip("-")[:60] or "car"
    if not files:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Select at least one photo")
    if len(files) > _MAX_FILES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Upload at most {_MAX_FILES} photos")

    folder = Path(settings.media_dir).resolve() / "cars" / safe
    folder.mkdir(parents=True, exist_ok=True)
    start = len([p for p in folder.iterdir() if p.suffix.lower() in (".jpg", ".png", ".webp")])
    base = settings.media_base_url.rstrip("/")

    urls: list[str] = []
    for offset, f in enumerate(files, start=1):
        if (f.content_type or "").lower() not in _EXT:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"Unsupported image type: {f.content_type or 'unknown'}")
        data = await f.read()
        if len(data) > _MAX_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                                f"{f.filename} exceeds the 8 MB limit")
        # Blur out auction-house signage in the background; output is always JPEG.
        processed = blur_background(data)
        name = f"{start + offset:02d}.jpg"
        (folder / name).write_bytes(processed)
        urls.append(f"{base}/media/cars/{safe}/{name}")
    return {"urls": urls}


@router.get("/duty-categories")
async def duty_categories(buyer: Annotated[User, Depends(require_buyer)]):
    """Vehicle categories and their customs-duty rates for the duty calculator."""
    return list_categories()


@router.post("/duty-quote", response_model=DutyQuoteOut)
async def duty_quote(payload: DutyQuoteRequest, buyer: Annotated[User, Depends(require_buyer)]):
    """Estimate ZIMRA customs duty + surtax + VAT for a Value-for-Duty (VDP) amount in USD."""
    return zim_duty(payload.vdp, category=payload.category,
                    vehicle_age_years=payload.vehicle_age_years,
                    surtax_applies=payload.surtax_applies)


@router.get("/listings", response_model=list[SaleListingAdminOut])
async def list_listings(user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    rows = (await db.execute(
        select(SaleListing).where(SaleListing.dealership_id == user.dealership_id)
        .order_by(SaleListing.id.desc())
    )).scalars().all()
    return rows


@router.post("/listings", response_model=SaleListingAdminOut, status_code=status.HTTP_201_CREATED)
async def create_listing(
    payload: SaleListingCreate,
    buyer: Annotated[User, Depends(require_buyer)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    vehicle = await db.get(Vehicle, payload.vehicle_id)
    if vehicle is None or vehicle.dealership_id != buyer.dealership_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehicle not found")

    data = payload.model_dump()
    data.pop("vehicle_id", None)
    listing = SaleListing(dealership_id=buyer.dealership_id, vehicle_id=vehicle.id, slug="pending",
                          **data)
    if listing.status == "PUBLISHED":
        listing.published_at = datetime.now(timezone.utc)
    db.add(listing)
    await db.flush()  # assigns id

    base = _slugify(" ".join(str(x) for x in (
        vehicle.model_year, vehicle.make, vehicle.model, vehicle.derivative) if x))
    listing.slug = f"{base}-{listing.id}"
    await db.flush()
    return listing


@router.get("/listings/{listing_id}", response_model=SaleListingAdminOut)
async def get_listing(listing_id: int, user: CurrentUser,
                      db: Annotated[AsyncSession, Depends(get_db)]):
    listing = await db.get(SaleListing, listing_id)
    if listing is None or listing.dealership_id != user.dealership_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not found")
    return listing


@router.patch("/listings/{listing_id}", response_model=SaleListingAdminOut)
async def update_listing(
    listing_id: int,
    payload: SaleListingUpdate,
    buyer: Annotated[User, Depends(require_buyer)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    listing = await db.get(SaleListing, listing_id)
    if listing is None or listing.dealership_id != buyer.dealership_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(listing, key, value)
    if listing.status == "PUBLISHED" and listing.published_at is None:
        listing.published_at = datetime.now(timezone.utc)
    if listing.status in _SOLD_STATES and listing.sold_at is None:
        listing.sold_at = datetime.now(timezone.utc)
    await db.flush()
    return listing


@router.get("/enquiries", response_model=list[EnquiryOut])
async def list_enquiries(user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    rows = (await db.execute(
        select(Enquiry).where(Enquiry.dealership_id == user.dealership_id)
        .order_by(Enquiry.id.desc())
    )).scalars().all()
    return rows


@router.get("/briefs", response_model=list[BuyerBriefOut])
async def list_briefs(user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    rows = (await db.execute(
        select(BuyerBrief).where(BuyerBrief.dealership_id == user.dealership_id)
        .order_by(BuyerBrief.id.desc())
    )).scalars().all()
    return rows
