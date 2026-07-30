"""Provider interfaces (Protocols) for pluggable data sources."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class VehicleIdentityProvider(Protocol):
    """Resolve basic vehicle identity from a registration (e.g. DVLA VES in production)."""

    name: str

    def lookup(self, registration: str) -> dict[str, Any] | None: ...


@runtime_checkable
class MotHistoryProvider(Protocol):
    """MOT test history (e.g. DVSA MOT History API in production)."""

    name: str

    def history(self, registration: str) -> dict[str, Any] | None: ...


@runtime_checkable
class VehicleHistoryProvider(Protocol):
    """Provenance / finance / write-off markers (e.g. a licensed HPI provider)."""

    name: str

    def check(self, registration: str, vin: str | None = None) -> dict[str, Any] | None: ...


@runtime_checkable
class ValuationProvider(Protocol):
    """Trade/retail valuations (e.g. CAP HPI in production)."""

    name: str

    def valuation(self, *, make: str, model: str, year: int, mileage: int) -> dict[str, Any] | None: ...


@runtime_checkable
class MarketComparablesProvider(Protocol):
    """Live retail comparables (e.g. Auto Trader retailer services in production)."""

    name: str

    def comparables(self, *, make: str, model: str, year: int,
                    mileage: int, limit: int = 5) -> list[dict[str, Any]]: ...


@runtime_checkable
class AuctionListingProvider(Protocol):
    """Auction catalogue feed (requires a commercial agreement in production)."""

    name: str

    def catalogue(self, auction_house: str) -> list[dict[str, Any]]: ...


@runtime_checkable
class DamageAnalysisProvider(Protocol):
    """Vehicle-photo damage analysis / intelligent advisor.

    ``images`` is a list of ``(media_type, base64_data)`` tuples; ``context`` carries the
    dealership/vehicle details so advice can be tailored. Returns a structured, clearly-labelled
    assessment of *visible* damage — never a substitute for a physical/mechanical inspection.
    """

    name: str

    def analyse(self, images: list[tuple[str, str]], context: dict[str, Any]) -> dict[str, Any]: ...
