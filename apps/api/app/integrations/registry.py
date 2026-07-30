"""Provider registry. Swaps mock adapters for licensed ones via configuration."""

from __future__ import annotations

from dataclasses import dataclass

from ..core.config import settings
from .ebay import EbayPartsProvider, MockPartsProvider
from .gov import DvlaVesIdentityProvider, DvsaMotHistoryProvider
from .mock import (
    MockAuctionListingProvider,
    MockMarketComparablesProvider,
    MockMotHistoryProvider,
    MockValuationProvider,
    MockVehicleHistoryProvider,
    MockVehicleIdentityProvider,
)
from .vision import ClaudeDamageAnalysisProvider, MockDamageAnalysisProvider


@dataclass
class Providers:
    identity: object
    mot: object
    history: object
    valuation: object
    comparables: object
    auction: object


_MOCK = Providers(
    identity=MockVehicleIdentityProvider(),
    mot=MockMotHistoryProvider(),
    history=MockVehicleHistoryProvider(),
    valuation=MockValuationProvider(),
    comparables=MockMarketComparablesProvider(),
    auction=MockAuctionListingProvider(),
)


def get_providers() -> Providers:
    """Return the active provider set.

    Vehicle identity uses DVLA VES and MOT uses DVSA when their credentials are configured;
    everything else stays on the deterministic mock adapters.
    """
    return Providers(
        identity=(DvlaVesIdentityProvider() if settings.dvla_ves_enabled else _MOCK.identity),
        mot=(DvsaMotHistoryProvider() if settings.dvsa_mot_enabled else _MOCK.mot),
        history=_MOCK.history,
        valuation=_MOCK.valuation,
        comparables=_MOCK.comparables,
        auction=_MOCK.auction,
    )


def get_damage_provider():
    """Claude vision when an API key is configured, otherwise the labelled mock adapter."""
    if settings.claude_vision_enabled:
        return ClaudeDamageAnalysisProvider(settings.anthropic_api_key, settings.anthropic_model)
    return MockDamageAnalysisProvider()


def get_parts_provider():
    """eBay Browse API when keys are configured, otherwise the labelled mock parts adapter."""
    return EbayPartsProvider() if settings.ebay_enabled else MockPartsProvider()
