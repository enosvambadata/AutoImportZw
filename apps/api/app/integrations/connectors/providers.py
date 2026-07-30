"""Real-provider connector templates: Copart, SYNETIQ, Auto Trader.

Each reads credentials from environment variables and is *configured* only when they are present.
The request + mapping skeleton is marked clearly — connecting a provider means (1) obtaining official
API access under a commercial agreement, (2) setting the env vars, and (3) implementing ``_map...`` to
translate that provider's response into the normalised shapes in ``base.py``. Until mapped, the
connector raises ``NotImplementedError`` with precise guidance rather than inventing data.

None of these scrape a website — they call the provider's official API with your credentials.
"""

from __future__ import annotations

import os
from typing import Any

from .base import NormalizedListing, NormalizedValuation


class _EnvConnector:
    def __init__(self, base_url: str | None, api_key: str | None,
                 client_secret: str | None = None):
        self.base_url = base_url
        self.api_key = api_key
        self.client_secret = client_secret

    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def _get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:  # pragma: no cover
        """Authenticated GET against the provider API. Fill auth to match the provider's scheme."""
        import httpx  # lazy import; only needed when a real connector is configured

        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
        with httpx.Client(base_url=self.base_url, headers=headers, timeout=30) as client:
            resp = client.get(path, params=params)
            resp.raise_for_status()
            return resp.json()


class CopartConnector(_EnvConnector):
    """Copart member/partner catalogue API.

    Access: a Copart business account with API/data-feed approval. Set COPART_API_URL and
    COPART_API_KEY (Copart's integration team provides the endpoint + credential scheme).
    """

    name = "copart"
    source = "COPART"

    def __init__(self):
        super().__init__(os.environ.get("COPART_API_URL"), os.environ.get("COPART_API_KEY"))

    def fetch_listings(self, *, since_iso: str | None = None,
                       limit: int = 200) -> list[NormalizedListing]:  # pragma: no cover
        if not self.is_configured():
            raise NotImplementedError(
                "Set COPART_API_URL and COPART_API_KEY (from your approved Copart data-feed "
                "agreement) to enable the Copart connector.")
        # data = self._get_json("/lots/upcoming", {"limit": limit})
        # return [self._map_lot(lot) for lot in data["lots"]]
        raise NotImplementedError(
            "Implement CopartConnector._map_lot() to translate Copart's lot payload into "
            "NormalizedListing (see the field reference in docs/API_INTEGRATIONS.md).")

    @staticmethod
    def _map_lot(lot: dict[str, Any]) -> NormalizedListing:  # pragma: no cover
        raise NotImplementedError("Map Copart lot fields to NormalizedListing.")


class SynetiqConnector(_EnvConnector):
    """SYNETIQ salvage-auction data feed.

    Access: a SYNETIQ trade/buyer account with data-feed access. Set SYNETIQ_API_URL and
    SYNETIQ_API_KEY.
    """

    name = "synetiq"
    source = "SYNETIQ"

    def __init__(self):
        super().__init__(os.environ.get("SYNETIQ_API_URL"), os.environ.get("SYNETIQ_API_KEY"))

    def fetch_listings(self, *, since_iso: str | None = None,
                       limit: int = 200) -> list[NormalizedListing]:  # pragma: no cover
        if not self.is_configured():
            raise NotImplementedError(
                "Set SYNETIQ_API_URL and SYNETIQ_API_KEY (from your SYNETIQ trade agreement) to "
                "enable the SYNETIQ connector.")
        raise NotImplementedError(
            "Implement SynetiqConnector._map_lot() to translate SYNETIQ's payload into "
            "NormalizedListing.")

    @staticmethod
    def _map_lot(lot: dict[str, Any]) -> NormalizedListing:  # pragma: no cover
        raise NotImplementedError("Map SYNETIQ lot fields to NormalizedListing.")


class AutoTraderConnector(_EnvConnector):
    """Auto Trader Connect — current retail pricing and comparables.

    Access: an Auto Trader trade account with Connect API keys. Auto Trader uses key+secret to mint a
    short-lived token. Set AUTOTRADER_API_URL, AUTOTRADER_API_KEY and AUTOTRADER_API_SECRET.
    """

    name = "autotrader"
    source = "AUTO_TRADER"

    def __init__(self):
        super().__init__(os.environ.get("AUTOTRADER_API_URL"), os.environ.get("AUTOTRADER_API_KEY"),
                         os.environ.get("AUTOTRADER_API_SECRET"))

    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.client_secret)

    def valuation(self, *, make: str, model: str, year: int, mileage: int,
                  derivative: str | None = None) -> NormalizedValuation:  # pragma: no cover
        if not self.is_configured():
            raise NotImplementedError(
                "Set AUTOTRADER_API_URL, AUTOTRADER_API_KEY and AUTOTRADER_API_SECRET (from your "
                "Auto Trader Connect account) to enable live valuations.")
        # token = self._authenticate()  # key+secret -> bearer token
        # data = self._get_json("/valuations", {...})
        # return self._map_valuation(data)
        raise NotImplementedError(
            "Implement AutoTraderConnector._map_valuation() to translate the Auto Trader response "
            "into NormalizedValuation.")

    # Compatibility with the existing mock ValuationProvider slot (dict shape used by /lookups).
    def valuation_dict(self, *, make: str, model: str, year: int,
                       mileage: int) -> dict[str, Any]:  # pragma: no cover
        v = self.valuation(make=make, model=model, year=year, mileage=mileage)
        return {
            "cap_clean": str(v.retail_high), "cap_average": str(v.retail_average),
            "cap_below": str(v.retail_low), "estimated_retail": str(v.retail_average),
            "data_source": "AUTO_TRADER",
        }
