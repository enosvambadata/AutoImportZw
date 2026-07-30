"""Provider connectors + registry.

Catalogue connectors pull upcoming auction lots; the valuation connector fetches current retail
pricing. Real providers activate only when their credentials are configured; the demo catalogue
connector is always available so the pipeline can run without credentials.
"""

from __future__ import annotations

from .base import CatalogueConnector, NormalizedListing, NormalizedValuation, ValuationConnector
from .demo import DemoCatalogueConnector
from .providers import AutoTraderConnector, CopartConnector, SynetiqConnector

# One instance per provider (cheap; they only hold env-derived config).
_CATALOGUE = {
    "demo": DemoCatalogueConnector(),
    "copart": CopartConnector(),
    "synetiq": SynetiqConnector(),
}
_VALUATION = {"autotrader": AutoTraderConnector()}


def get_catalogue_connector(name: str) -> CatalogueConnector | None:
    return _CATALOGUE.get(name.lower())


def get_valuation_connector(name: str = "autotrader") -> ValuationConnector | None:
    return _VALUATION.get(name.lower())


def connector_status() -> list[dict]:
    """Report every connector and whether its credentials are configured."""
    rows = []
    for kind, table in (("catalogue", _CATALOGUE), ("valuation", _VALUATION)):
        for name, conn in table.items():
            rows.append({
                "name": name,
                "kind": kind,
                "source": conn.source,
                "configured": conn.is_configured(),
                "demo": name == "demo",
            })
    return rows


__all__ = [
    "CatalogueConnector",
    "ValuationConnector",
    "NormalizedListing",
    "NormalizedValuation",
    "AutoTraderConnector",
    "CopartConnector",
    "SynetiqConnector",
    "DemoCatalogueConnector",
    "get_catalogue_connector",
    "get_valuation_connector",
    "connector_status",
]
