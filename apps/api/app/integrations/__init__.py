"""Data-provider integration layer.

All external data sources sit behind interfaces (Protocols). The MVP ships deterministic MOCK
adapters that clearly label their provenance (``MOCK_ADAPTER``). Placeholder adapters document
where licensed integrations (DVLA, DVSA MOT, CAP HPI, Auto Trader, auction feeds) would connect.
No adapter scrapes websites or bypasses access controls.
"""

from .base import (
    AuctionListingProvider,
    DamageAnalysisProvider,
    MarketComparablesProvider,
    MotHistoryProvider,
    ValuationProvider,
    VehicleHistoryProvider,
    VehicleIdentityProvider,
)
from .registry import get_damage_provider, get_parts_provider, get_providers

__all__ = [
    "VehicleIdentityProvider",
    "MotHistoryProvider",
    "VehicleHistoryProvider",
    "ValuationProvider",
    "MarketComparablesProvider",
    "AuctionListingProvider",
    "DamageAnalysisProvider",
    "get_providers",
    "get_damage_provider",
    "get_parts_provider",
]
