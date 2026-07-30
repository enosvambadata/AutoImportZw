"""Auction houses, fee bands, vehicles, vehicle history and auction listings."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base, IntPKMixin, TimestampMixin


class AuctionHouse(Base, IntPKMixin, TimestampMixin):
    __tablename__ = "auction_houses"

    dealership_id: Mapped[int] = mapped_column(ForeignKey("dealerships.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    website: Mapped[str | None] = mapped_column(String(255))
    postcode: Mapped[str | None] = mapped_column(String(12))  # site location for distance/transport
    fee_calc_type: Mapped[str] = mapped_column(String(30), default="PERCENTAGE")
    default_transport_estimate: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("150"))
    notes: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    fee_bands: Mapped[list[AuctionFeeBand]] = relationship(
        back_populates="auction_house", cascade="all, delete-orphan")


class AuctionFeeBand(Base, IntPKMixin, TimestampMixin):
    __tablename__ = "auction_fee_bands"

    auction_house_id: Mapped[int] = mapped_column(ForeignKey("auction_houses.id"), index=True)
    label: Mapped[str | None] = mapped_column(String(120))
    fixed_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    percentage: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=Decimal("0"))
    minimum_fee: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    maximum_fee: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    lower_bound: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    upper_bound: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    vat_applicable: Mapped[bool] = mapped_column(Boolean, default=True)
    stated_inclusive: Mapped[bool] = mapped_column(Boolean, default=False)
    effective_start: Mapped[date | None] = mapped_column(Date)
    effective_end: Mapped[date | None] = mapped_column(Date)

    auction_house: Mapped[AuctionHouse] = relationship(back_populates="fee_bands")


class Vehicle(Base, IntPKMixin, TimestampMixin):
    __tablename__ = "vehicles"

    dealership_id: Mapped[int] = mapped_column(ForeignKey("dealerships.id"), index=True)
    registration: Mapped[str | None] = mapped_column(String(12))
    vin: Mapped[str | None] = mapped_column(String(20))
    make: Mapped[str] = mapped_column(String(60))
    model: Mapped[str] = mapped_column(String(80))
    derivative: Mapped[str | None] = mapped_column(String(120))
    registration_date: Mapped[date | None] = mapped_column(Date)
    model_year: Mapped[int | None] = mapped_column(Integer)
    mileage: Mapped[int | None] = mapped_column(Integer)
    fuel_type: Mapped[str | None] = mapped_column(String(30))
    transmission: Mapped[str | None] = mapped_column(String(30))
    engine_size: Mapped[int | None] = mapped_column(Integer)  # cc
    body_type: Mapped[str | None] = mapped_column(String(40))
    colour: Mapped[str | None] = mapped_column(String(40))
    previous_keepers: Mapped[int | None] = mapped_column(Integer)
    number_of_keys: Mapped[int | None] = mapped_column(Integer)
    euro_status: Mapped[str | None] = mapped_column(String(10))
    ulez_compliant: Mapped[bool | None] = mapped_column(Boolean)
    category_marker: Mapped[str | None] = mapped_column(String(4))  # N, S, A, B
    imported: Mapped[bool] = mapped_column(Boolean, default=False)
    data_source: Mapped[str] = mapped_column(String(20), default="MANUAL")
    notes: Mapped[str | None] = mapped_column(Text)  # seller description / free-text captured from a listing

    history: Mapped[VehicleHistory | None] = relationship(
        back_populates="vehicle", uselist=False, cascade="all, delete-orphan")


class VehicleHistory(Base, IntPKMixin, TimestampMixin):
    __tablename__ = "vehicle_histories"

    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), unique=True, index=True)
    mot_expiry: Mapped[date | None] = mapped_column(Date)
    mot_tests: Mapped[list | None] = mapped_column(
        JSON, default=list, server_default=text("'[]'"))  # per-test history (date/result/odometer)
    mot_pass_count: Mapped[int] = mapped_column(Integer, default=0)
    mot_fail_count: Mapped[int] = mapped_column(Integer, default=0)
    advisory_count: Mapped[int] = mapped_column(Integer, default=0)
    major_defect_count: Mapped[int] = mapped_column(Integer, default=0)
    dangerous_defect_count: Mapped[int] = mapped_column(Integer, default=0)
    repeated_failures: Mapped[bool] = mapped_column(Boolean, default=False)
    outstanding_recall: Mapped[bool] = mapped_column(Boolean, default=False)
    finance_marker: Mapped[bool] = mapped_column(Boolean, default=False)
    stolen_marker: Mapped[bool] = mapped_column(Boolean, default=False)
    write_off_marker: Mapped[bool] = mapped_column(Boolean, default=False)
    mileage_discrepancy: Mapped[bool] = mapped_column(Boolean, default=False)
    plate_changes: Mapped[int] = mapped_column(Integer, default=0)
    keeper_changes: Mapped[int] = mapped_column(Integer, default=0)
    service_history_status: Mapped[str | None] = mapped_column(String(20))  # FULL/PARTIAL/NONE
    last_service_date: Mapped[date | None] = mapped_column(Date)
    last_service_mileage: Mapped[int | None] = mapped_column(Integer)
    history_provider: Mapped[str] = mapped_column(String(40), default="MOCK_ADAPTER")
    data_retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    vehicle: Mapped[Vehicle] = relationship(back_populates="history")


class AuctionListing(Base, IntPKMixin, TimestampMixin):
    __tablename__ = "auction_listings"

    dealership_id: Mapped[int] = mapped_column(ForeignKey("dealerships.id"), index=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), index=True)
    auction_house_id: Mapped[int] = mapped_column(ForeignKey("auction_houses.id"), index=True)
    lot_number: Mapped[str | None] = mapped_column(String(20))
    auction_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    guide_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    cap_clean: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    cap_average: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    cap_below: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    estimated_retail: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    starting_bid: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    reserve_status: Mapped[str | None] = mapped_column(String(20))
    condition_grade: Mapped[int | None] = mapped_column(Integer)  # 1 best .. 5 worst
    mechanical_report: Mapped[str | None] = mapped_column(Text)
    seller_declaration: Mapped[str | None] = mapped_column(Text)
    runner_status: Mapped[str | None] = mapped_column(String(20))  # RUNNER/NON_RUNNER/UNKNOWN
    vat_status: Mapped[str] = mapped_column(String(20), default="MARGIN")
    direct_url: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    listing_status: Mapped[str] = mapped_column(String(20), default="UPCOMING")
    data_source: Mapped[str] = mapped_column(String(20), default="MANUAL")
    image_urls: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"))  # real provider photo URLs
    spin_urls: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"))  # ordered 360° frame URLs

    vehicle: Mapped[Vehicle] = relationship()
    auction_house: Mapped[AuctionHouse] = relationship()
