"""Schemas for the import-concierge storefront (admin CRUD + public read/write)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from .common import ORMModel

# ---------------------------------------------------------------------------
# Admin (authenticated) — manage candidate listings
# ---------------------------------------------------------------------------


class LandedCostIn(BaseModel):
    vehicle_price: Decimal = Field(default=Decimal("0"), ge=0)
    auction_fees: Decimal = Field(default=Decimal("0"), ge=0)
    uk_transport: Decimal = Field(default=Decimal("0"), ge=0)
    ocean_freight: Decimal = Field(default=Decimal("0"), ge=0)
    import_duty: Decimal = Field(default=Decimal("0"), ge=0)
    import_surtax: Decimal = Field(default=Decimal("0"), ge=0)
    import_vat: Decimal = Field(default=Decimal("0"), ge=0)
    inland_transport: Decimal = Field(default=Decimal("0"), ge=0)
    estimated_repairs: Decimal = Field(default=Decimal("0"), ge=0)
    service_fee: Decimal = Field(default=Decimal("0"), ge=0)


class SaleListingCreate(LandedCostIn):
    vehicle_id: int
    appraisal_id: int | None = None
    headline: str = Field(min_length=3, max_length=200)
    blurb: str | None = None
    video_url: str | None = Field(default=None, max_length=500)
    image_urls: list[str] = Field(default_factory=list)
    currency: str = Field(default="USD", max_length=3)
    status: str = "DRAFT"
    dest_country: str = "Zimbabwe"
    dest_port: str | None = None
    dest_city: str | None = None


class SaleListingUpdate(BaseModel):
    headline: str | None = Field(default=None, min_length=3, max_length=200)
    blurb: str | None = None
    video_url: str | None = Field(default=None, max_length=500)
    image_urls: list[str] | None = None
    currency: str | None = Field(default=None, max_length=3)
    status: str | None = None
    dest_country: str | None = None
    dest_port: str | None = None
    dest_city: str | None = None
    vehicle_price: Decimal | None = Field(default=None, ge=0)
    auction_fees: Decimal | None = Field(default=None, ge=0)
    uk_transport: Decimal | None = Field(default=None, ge=0)
    ocean_freight: Decimal | None = Field(default=None, ge=0)
    import_duty: Decimal | None = Field(default=None, ge=0)
    import_surtax: Decimal | None = Field(default=None, ge=0)
    import_vat: Decimal | None = Field(default=None, ge=0)
    inland_transport: Decimal | None = Field(default=None, ge=0)
    estimated_repairs: Decimal | None = Field(default=None, ge=0)
    service_fee: Decimal | None = Field(default=None, ge=0)


class SaleListingAdminOut(ORMModel):
    id: int
    vehicle_id: int
    appraisal_id: int | None = None
    slug: str
    status: str
    headline: str
    blurb: str | None = None
    video_url: str | None = None
    image_urls: list[str] = []
    currency: str
    vehicle_price: Decimal
    auction_fees: Decimal
    uk_transport: Decimal
    ocean_freight: Decimal
    import_duty: Decimal
    import_surtax: Decimal
    import_vat: Decimal
    inland_transport: Decimal
    estimated_repairs: Decimal
    service_fee: Decimal
    dest_country: str
    dest_port: str | None = None
    dest_city: str | None = None
    published_at: datetime | None = None
    sold_at: datetime | None = None


class EnquiryOut(ORMModel):
    id: int
    sale_listing_id: int | None = None
    name: str
    contact: str
    message: str | None = None
    deposit_amount: Decimal | None = None
    deposit_status: str
    status: str
    created_at: datetime


class BuyerBriefOut(ORMModel):
    id: int
    name: str
    contact: str
    make: str | None = None
    model: str | None = None
    budget_usd: Decimal | None = None
    source_url: str | None = None
    notes: str | None = None
    status: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Public (unauthenticated) — browse + enquire
# ---------------------------------------------------------------------------


class PublicMotTest(BaseModel):
    date: str | None = None
    result: str | None = None
    odometer: int | None = None
    unit: str | None = None
    expiry: str | None = None
    advisories: int = 0
    dangerous: int = 0


class PublicMot(BaseModel):
    expiry: str | None = None
    pass_count: int = 0
    fail_count: int = 0
    advisory_count: int = 0
    dangerous_defect_count: int = 0
    tests: list[PublicMotTest] = []


class PublicLanded(BaseModel):
    currency: str
    vehicle_price: Decimal
    auction_fees: Decimal
    uk_transport: Decimal
    ocean_freight: Decimal
    import_duty: Decimal
    import_surtax: Decimal
    import_vat: Decimal
    inland_transport: Decimal
    estimated_repairs: Decimal
    service_fee: Decimal
    total: Decimal
    dest_country: str
    dest_port: str | None = None
    dest_city: str | None = None


class DutyQuoteRequest(BaseModel):
    vdp: Decimal = Field(ge=0)                 # Value for Duty Purposes (car + freight + insurance)
    category: str = "CAR"
    vehicle_age_years: int | None = Field(default=None, ge=0, le=100)
    surtax_applies: bool | None = None


class DutyQuoteOut(BaseModel):
    category: str
    duty_rate: str
    vdp: Decimal
    customs_duty: Decimal
    surtax: Decimal
    vat: Decimal
    total_taxes: Decimal


class PublicCarSummary(BaseModel):
    slug: str
    status: str
    headline: str
    make: str
    model: str
    derivative: str | None = None
    model_year: int | None = None
    mileage: int | None = None
    fuel_type: str | None = None
    transmission: str | None = None
    colour: str | None = None
    currency: str
    landed_total: Decimal
    dest_city: str | None = None
    dest_country: str
    has_video: bool = False
    thumb: str | None = None


class PublicCarDetail(PublicCarSummary):
    blurb: str | None = None
    video_url: str | None = None
    images: list[str] = []
    category_marker: str | None = None
    registration: str | None = None
    notes: str | None = None
    mot: PublicMot | None = None
    landed: PublicLanded


class EnquiryCreate(BaseModel):
    slug: str | None = None
    name: str = Field(min_length=1, max_length=120)
    contact: str = Field(min_length=3, max_length=200)
    message: str | None = Field(default=None, max_length=2000)
    company: str | None = None  # honeypot — must stay empty; bots fill it


class BuyerBriefCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    contact: str = Field(min_length=3, max_length=200)
    make: str | None = Field(default=None, max_length=60)
    model: str | None = Field(default=None, max_length=80)
    budget_usd: Decimal | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=2000)
    company: str | None = None  # honeypot


class VetRequestCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    contact: str = Field(min_length=3, max_length=200)
    source_url: str | None = Field(default=None, max_length=500)
    listing_text: str | None = Field(default=None, max_length=8000)
    company: str | None = None  # honeypot


class PublicStats(BaseModel):
    delivered: int
    available: int
    destinations: list[str]
