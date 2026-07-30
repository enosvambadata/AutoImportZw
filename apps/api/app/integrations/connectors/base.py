"""Connector interfaces and the normalised shapes every provider maps into.

A connector's only job is to authenticate against a provider's *official* API and return data in
these normalised shapes. The ingestion service then upserts them into the database, after which the
whole platform (shortlist, appraisals, analytics) runs on the persisted rows — regardless of which
provider (or CSV) supplied them. No connector scrapes a website or bypasses access controls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable


@dataclass
class NormalizedListing:
    """One auction lot, normalised across providers."""

    source: str                      # e.g. "COPART", "SYNETIQ", "CSV_IMPORT", "DEMO"
    auction_house_name: str
    lot_number: str
    # Vehicle identity
    make: str
    model: str
    registration: str | None = None
    vin: str | None = None
    derivative: str | None = None
    model_year: int | None = None
    mileage: int | None = None
    fuel_type: str | None = None
    transmission: str | None = None
    colour: str | None = None
    category_marker: str | None = None  # N / S / A / B
    # Listing detail
    auction_datetime_iso: str | None = None
    guide_price: Decimal | None = None
    cap_clean: Decimal | None = None
    cap_average: Decimal | None = None
    cap_below: Decimal | None = None
    estimated_retail: Decimal | None = None
    condition_grade: int | None = None
    runner_status: str | None = None    # RUNNER / NON_RUNNER / UNKNOWN
    vat_status: str = "MARGIN"
    direct_url: str | None = None
    notes: str | None = None
    image_urls: list[str] = field(default_factory=list)
    spin_urls: list[str] = field(default_factory=list)


@dataclass
class NormalizedValuation:
    source: str
    retail_low: Decimal
    retail_average: Decimal
    retail_high: Decimal
    trade_average: Decimal | None = None
    sample_size: int | None = None
    comparables: list[dict[str, Any]] = field(default_factory=list)


@runtime_checkable
class CatalogueConnector(Protocol):
    """Pulls upcoming auction lots from a provider's official catalogue API."""

    name: str
    source: str

    def is_configured(self) -> bool: ...

    def fetch_listings(self, *, since_iso: str | None = None,
                       limit: int = 200) -> list[NormalizedListing]: ...


@runtime_checkable
class ValuationConnector(Protocol):
    """Fetches current retail pricing / comparables from a provider's official API."""

    name: str
    source: str

    def is_configured(self) -> bool: ...

    def valuation(self, *, make: str, model: str, year: int,
                  mileage: int, derivative: str | None = None) -> NormalizedValuation: ...
