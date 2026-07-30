"""Auction house, fee band, vehicle, history and listing schemas."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from .common import ORMModel

# UK current-format plate + common older formats (loose but rejects obvious junk).
UK_REG_RE = re.compile(r"^[A-Z0-9]{1,3}\s?[A-Z0-9]{1,4}$", re.IGNORECASE)
VIN_RE = re.compile(r"^[A-HJ-NPR-Z0-9]{11,17}$", re.IGNORECASE)


# ---- Fee bands ----
class FeeBandBase(BaseModel):
    label: str | None = None
    fixed_fee: Decimal = Field(default=Decimal("0"), ge=0)
    percentage: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    minimum_fee: Decimal | None = Field(default=None, ge=0)
    maximum_fee: Decimal | None = Field(default=None, ge=0)
    lower_bound: Decimal | None = Field(default=None, ge=0)
    upper_bound: Decimal | None = Field(default=None, ge=0)
    vat_applicable: bool = True
    stated_inclusive: bool = False
    effective_start: date | None = None
    effective_end: date | None = None


class FeeBandCreate(FeeBandBase):
    pass


class FeeBandOut(FeeBandBase, ORMModel):
    id: int
    auction_house_id: int


# ---- Auction houses ----
class AuctionHouseBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    website: str | None = None
    postcode: str | None = None
    fee_calc_type: str = "PERCENTAGE"
    default_transport_estimate: Decimal = Field(default=Decimal("150"), ge=0)
    notes: str | None = None
    active: bool = True


class AuctionHouseCreate(AuctionHouseBase):
    fee_bands: list[FeeBandCreate] = Field(default_factory=list)


class AuctionHouseUpdate(BaseModel):
    name: str | None = None
    website: str | None = None
    postcode: str | None = None
    fee_calc_type: str | None = None
    default_transport_estimate: Decimal | None = Field(default=None, ge=0)
    notes: str | None = None
    active: bool | None = None


class AuctionHouseOut(AuctionHouseBase, ORMModel):
    id: int
    fee_bands: list[FeeBandOut] = Field(default_factory=list)


# ---- Vehicle history ----
class MotTestOut(BaseModel):
    date: str | None = None
    result: str | None = None
    odometer: int | None = None
    unit: str | None = None
    expiry: str | None = None
    advisories: int = 0
    dangerous: int = 0


class VehicleHistoryBase(BaseModel):
    mot_expiry: date | None = None
    mot_tests: list[MotTestOut] = []
    mot_pass_count: int = 0
    mot_fail_count: int = 0
    advisory_count: int = 0
    major_defect_count: int = 0
    dangerous_defect_count: int = 0
    repeated_failures: bool = False
    outstanding_recall: bool = False
    finance_marker: bool = False
    stolen_marker: bool = False
    write_off_marker: bool = False
    mileage_discrepancy: bool = False
    plate_changes: int = 0
    keeper_changes: int = 0
    service_history_status: str | None = None
    last_service_date: date | None = None
    last_service_mileage: int | None = None
    history_provider: str = "MOCK_ADAPTER"


class VehicleHistoryOut(VehicleHistoryBase, ORMModel):
    id: int
    vehicle_id: int
    data_retrieved_at: datetime | None = None


# ---- Vehicles ----
class VehicleBase(BaseModel):
    registration: str | None = None
    vin: str | None = None
    make: str = Field(min_length=1, max_length=60)
    model: str = Field(min_length=1, max_length=80)
    derivative: str | None = None
    registration_date: date | None = None
    model_year: int | None = Field(default=None, ge=1950, le=2100)
    mileage: int | None = Field(default=None, ge=0, le=1_000_000)
    fuel_type: str | None = None
    transmission: str | None = None
    engine_size: int | None = None
    body_type: str | None = None
    colour: str | None = None
    previous_keepers: int | None = Field(default=None, ge=0)
    number_of_keys: int | None = Field(default=None, ge=0)
    euro_status: str | None = None
    ulez_compliant: bool | None = None
    category_marker: str | None = None
    imported: bool = False
    notes: str | None = None

    @field_validator("registration")
    @classmethod
    def _reg(cls, v):
        if v is None or v.strip() == "":
            return None
        v = v.upper().strip()
        if not UK_REG_RE.match(v.replace(" ", "")):
            raise ValueError("Registration does not look like a valid UK plate")
        return v

    @field_validator("vin")
    @classmethod
    def _vin(cls, v):
        if v is None or v.strip() == "":
            return None
        v = v.upper().strip()
        if not VIN_RE.match(v):
            raise ValueError("VIN must be 11-17 characters and exclude I, O and Q")
        return v

    @field_validator("category_marker")
    @classmethod
    def _cat(cls, v):
        if v is None or v.strip() == "":
            return None
        v = v.upper().strip()
        if v not in {"N", "S", "A", "B"}:
            raise ValueError("Category marker must be one of N, S, A, B")
        return v


class VehicleCreate(VehicleBase):
    data_source: str = "MANUAL"
    history: VehicleHistoryBase | None = None


class VehicleUpdate(BaseModel):
    make: str | None = None
    model: str | None = None
    derivative: str | None = None
    mileage: int | None = None
    colour: str | None = None
    number_of_keys: int | None = None
    category_marker: str | None = None
    imported: bool | None = None


class VehicleOut(VehicleBase, ORMModel):
    id: int
    dealership_id: int
    data_source: str
    created_at: datetime
    history: VehicleHistoryOut | None = None


# ---- Auction listings ----
class AuctionListingBase(BaseModel):
    lot_number: str | None = None
    auction_datetime: datetime | None = None
    guide_price: Decimal | None = Field(default=None, ge=0)
    cap_clean: Decimal | None = Field(default=None, ge=0)
    cap_average: Decimal | None = Field(default=None, ge=0)
    cap_below: Decimal | None = Field(default=None, ge=0)
    estimated_retail: Decimal | None = Field(default=None, ge=0)
    starting_bid: Decimal | None = Field(default=None, ge=0)
    reserve_status: str | None = None
    condition_grade: int | None = Field(default=None, ge=1, le=5)
    mechanical_report: str | None = None
    seller_declaration: str | None = None
    runner_status: str | None = None
    vat_status: str = "MARGIN"
    direct_url: str | None = None
    notes: str | None = None
    listing_status: str = "UPCOMING"
    image_urls: list[str] = Field(default_factory=list)
    spin_urls: list[str] = Field(default_factory=list)

    @field_validator("image_urls", "spin_urls", mode="before")
    @classmethod
    def _coerce_list(cls, v):
        return v or []


class AuctionListingCreate(AuctionListingBase):
    vehicle_id: int
    auction_house_id: int
    data_source: str = "MANUAL"


class QuickAddListing(BaseModel):
    """One-step add of a lot you're watching (e.g. keyed from SYNETIQ's site)."""

    make: str = Field(min_length=1, max_length=60)
    model: str = Field(min_length=1, max_length=80)
    registration: str | None = None
    derivative: str | None = None
    model_year: int | None = Field(default=None, ge=1950, le=2100)
    mileage: int | None = Field(default=None, ge=0)
    fuel_type: str | None = None
    transmission: str | None = None
    guide_price: Decimal | None = Field(default=None, ge=0)
    lot_number: str | None = None
    auction_house: str = "SYNETIQ"
    category_marker: str | None = None
    runner_status: str | None = None
    notes: str | None = None


class AuctionListingUpdate(BaseModel):
    guide_price: Decimal | None = None
    condition_grade: int | None = None
    listing_status: str | None = None
    notes: str | None = None
    starting_bid: Decimal | None = None


class AuctionListingOut(AuctionListingBase, ORMModel):
    id: int
    dealership_id: int
    vehicle_id: int
    auction_house_id: int
    data_source: str
    vehicle: VehicleOut | None = None
    auction_house: AuctionHouseOut | None = None
