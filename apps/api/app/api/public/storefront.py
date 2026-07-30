"""Public storefront endpoints — browse candidates, check MOT, submit enquiries/briefs."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.ratelimit import rate_limit_mot_check, rate_limit_public_write
from ...db.session import get_db
from ...integrations import get_providers
from ...models.catalogue import Vehicle
from ...models.organisation import Dealership
from ...models.storefront import BuyerBrief, Enquiry, SaleListing
from ...schemas.storefront import (
    BuyerBriefCreate,
    EnquiryCreate,
    PublicCarDetail,
    PublicCarSummary,
    PublicLanded,
    PublicMot,
    PublicStats,
    VetRequestCreate,
)

router = APIRouter(tags=["storefront-public"])

CATALOGUE_STATES = ("PUBLISHED", "RESERVED")
VISIBLE_STATES = ("PUBLISHED", "RESERVED", "SOURCING", "SHIPPED", "DELIVERED")


def _summary(listing: SaleListing) -> PublicCarSummary:
    v = listing.vehicle
    images = listing.image_urls or []
    return PublicCarSummary(
        slug=listing.slug, status=listing.status, headline=listing.headline,
        make=v.make, model=v.model, derivative=v.derivative, model_year=v.model_year,
        mileage=v.mileage, fuel_type=v.fuel_type, transmission=v.transmission, colour=v.colour,
        currency=listing.currency, landed_total=listing.landed_total,
        dest_city=listing.dest_city, dest_country=listing.dest_country,
        has_video=bool(listing.video_url), thumb=(images[0] if images else None),
    )


def _mot(v: Vehicle) -> PublicMot | None:
    h = v.history
    if h is None:
        return None
    return PublicMot(
        expiry=h.mot_expiry.isoformat() if h.mot_expiry else None,
        pass_count=h.mot_pass_count, fail_count=h.mot_fail_count,
        advisory_count=h.advisory_count, dangerous_defect_count=h.dangerous_defect_count,
        tests=h.mot_tests or [],
    )


def _detail(listing: SaleListing) -> PublicCarDetail:
    v = listing.vehicle
    landed = PublicLanded(
        currency=listing.currency, vehicle_price=listing.vehicle_price,
        auction_fees=listing.auction_fees, uk_transport=listing.uk_transport,
        ocean_freight=listing.ocean_freight, import_duty=listing.import_duty,
        import_surtax=listing.import_surtax, import_vat=listing.import_vat,
        inland_transport=listing.inland_transport, estimated_repairs=listing.estimated_repairs,
        service_fee=listing.service_fee, total=listing.landed_total,
        dest_country=listing.dest_country, dest_port=listing.dest_port, dest_city=listing.dest_city,
    )
    return PublicCarDetail(
        **_summary(listing).model_dump(),
        blurb=listing.blurb, video_url=listing.video_url, images=listing.image_urls or [],
        category_marker=v.category_marker, registration=v.registration, notes=v.notes,
        mot=_mot(v), landed=landed,
    )


async def _resolve_dealership(db: AsyncSession, listing: SaleListing | None) -> int | None:
    if listing is not None:
        return listing.dealership_id
    return (await db.execute(select(Dealership.id).order_by(Dealership.id).limit(1))).scalar_one_or_none()


@router.get("/cars", response_model=list[PublicCarSummary])
async def public_cars(
    db: Annotated[AsyncSession, Depends(get_db)],
    make: str | None = None,
    max_price: float | None = Query(default=None, ge=0),
):
    stmt = (select(SaleListing).options(selectinload(SaleListing.vehicle))
            .join(Vehicle, Vehicle.id == SaleListing.vehicle_id)
            .where(SaleListing.status.in_(CATALOGUE_STATES)).order_by(SaleListing.published_at.desc()))
    if make:
        stmt = stmt.where(Vehicle.make == make)
    listings = (await db.execute(stmt)).scalars().all()
    out = [_summary(x) for x in listings]
    if max_price is not None:
        out = [c for c in out if float(c.landed_total) <= max_price]
    return out


@router.get("/delivered", response_model=list[PublicCarSummary])
async def public_delivered(db: Annotated[AsyncSession, Depends(get_db)], limit: int = 6):
    listings = (await db.execute(
        select(SaleListing).options(selectinload(SaleListing.vehicle))
        .where(SaleListing.status == "DELIVERED")
        .order_by(SaleListing.sold_at.desc().nullslast(), SaleListing.id.desc()).limit(limit)
    )).scalars().all()
    return [_summary(x) for x in listings]


@router.get("/cars/{slug}", response_model=PublicCarDetail)
async def public_car(slug: str, db: Annotated[AsyncSession, Depends(get_db)]):
    listing = (await db.execute(
        select(SaleListing)
        .options(selectinload(SaleListing.vehicle).selectinload(Vehicle.history))
        .where(SaleListing.slug == slug, SaleListing.status.in_(VISIBLE_STATES))
    )).scalar_one_or_none()
    if listing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Car not found")
    return _detail(listing)


@router.get("/stats", response_model=PublicStats)
async def public_stats(db: Annotated[AsyncSession, Depends(get_db)]):
    listings = (await db.execute(
        select(SaleListing.status, SaleListing.dest_country))).all()
    delivered = sum(1 for s, _ in listings if s == "DELIVERED")
    available = sum(1 for s, _ in listings if s in CATALOGUE_STATES)
    destinations = sorted({d for _, d in listings if d})
    return PublicStats(delivered=delivered, available=available,
                       destinations=destinations or ["Zimbabwe"])


@router.get("/check", response_model=PublicMot, dependencies=[Depends(rate_limit_mot_check)])
async def public_mot_check(reg: str = Query(min_length=2, max_length=10)):
    """Public MOT/registration checker — our equivalent of a VIN checker."""
    data = get_providers().mot.history(reg)
    if not data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No MOT record found for that registration")
    return PublicMot(
        expiry=data.get("mot_expiry"), pass_count=data.get("mot_pass_count", 0),
        fail_count=data.get("mot_fail_count", 0), advisory_count=data.get("advisory_count", 0),
        dangerous_defect_count=data.get("dangerous_defect_count", 0),
        tests=data.get("mot_tests") or [],
    )


@router.post("/enquiries", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(rate_limit_public_write)])
async def create_enquiry(payload: EnquiryCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    if payload.company:  # honeypot tripped — pretend success, store nothing
        return {"ok": True, "id": None, "message": "Thanks — we'll be in touch shortly."}
    listing: SaleListing | None = None
    if payload.slug:
        listing = (await db.execute(
            select(SaleListing).where(SaleListing.slug == payload.slug))).scalar_one_or_none()
    enquiry = Enquiry(
        dealership_id=await _resolve_dealership(db, listing),
        sale_listing_id=listing.id if listing else None,
        name=payload.name.strip(), contact=payload.contact.strip(),
        message=(payload.message or None),
    )
    db.add(enquiry)
    await db.flush()
    return {"ok": True, "id": enquiry.id,
            "message": "Thanks — we'll be in touch shortly to talk you through the next steps."}


@router.post("/briefs", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(rate_limit_public_write)])
async def create_brief(payload: BuyerBriefCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    if payload.company:
        return {"ok": True, "id": None, "message": "Brief received — we'll be in touch."}
    brief = BuyerBrief(
        dealership_id=await _resolve_dealership(db, None),
        name=payload.name.strip(), contact=payload.contact.strip(),
        make=payload.make, model=payload.model, budget_usd=payload.budget_usd,
        notes=(payload.notes or None),
    )
    db.add(brief)
    await db.flush()
    return {"ok": True, "id": brief.id,
            "message": "Brief received — we'll start sourcing and send you vetted options."}


@router.post("/vet-request", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(rate_limit_public_write)])
async def create_vet_request(payload: VetRequestCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    """A buyer found a car (auction link or pasted listing) and wants us to vet it and quote it."""
    if payload.company:
        return {"ok": True, "id": None, "message": "Got it — we'll be in touch."}
    if not (payload.source_url or payload.listing_text):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Paste the car's link or its listing details")
    brief = BuyerBrief(
        dealership_id=await _resolve_dealership(db, None),
        name=payload.name.strip(), contact=payload.contact.strip(),
        source_url=(payload.source_url.strip() if payload.source_url else None),
        notes=(payload.listing_text.strip() if payload.listing_text else None),
        status="VET",
    )
    db.add(brief)
    await db.flush()
    return {"ok": True, "id": brief.id,
            "message": ("Got it — we'll vet the car (MOT, write-off, condition) and send you a full "
                        "landed-cost quote.")}
