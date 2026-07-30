"""eBay parts sourcing via the official Browse API (free developer keys).

Given a search like "Ford Focus 2019 front bumper", returns matching used-part listings with prices so
a dealer can budget repairs from real market prices. Uses OAuth2 client-credentials (application
token). When no keys are configured, a labelled mock provider returns demo results whose links point
to eBay's own public search — no scraping.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

from ..core.config import settings

MOCK_SOURCE = "MOCK_ADAPTER"
EBAY_SOURCE = "EBAY"

_ENDPOINTS = {
    "production": {
        "token": "https://api.ebay.com/identity/v1/oauth2/token",
        "browse": "https://api.ebay.com/buy/browse/v1/item_summary/search",
    },
    "sandbox": {
        "token": "https://api.sandbox.ebay.com/identity/v1/oauth2/token",
        "browse": "https://api.sandbox.ebay.com/buy/browse/v1/item_summary/search",
    },
}


def _ebay_search_url(query: str) -> str:
    return f"https://www.ebay.co.uk/sch/i.html?_nkw={quote_plus(query)}"


class MockPartsProvider:
    name = "mock-parts"
    source = MOCK_SOURCE

    def is_configured(self) -> bool:
        return True

    def search(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        seed = sum(ord(c) for c in query) or 1
        conditions = ["Used", "Used - good", "Remanufactured"]
        items = []
        for i in range(min(max(1, limit), 4)):
            items.append({
                "title": f"{query} (used OEM)",
                "price": float(round(35 + (seed * (i + 3)) % 220, 2)),
                "currency": "GBP",
                "condition": conditions[i % len(conditions)],
                "url": _ebay_search_url(query),
                "image": None,
                "source": MOCK_SOURCE,
            })
        return items


class EbayPartsProvider:
    name = "ebay"
    source = EBAY_SOURCE

    def is_configured(self) -> bool:
        return settings.ebay_enabled

    def _token(self) -> str | None:  # pragma: no cover - needs keys
        import base64

        import httpx

        env = _ENDPOINTS.get(settings.ebay_env, _ENDPOINTS["production"])
        creds = base64.b64encode(
            f"{settings.ebay_client_id}:{settings.ebay_client_secret}".encode()).decode()
        try:
            resp = httpx.post(
                env["token"],
                headers={"Authorization": f"Basic {creds}",
                         "Content-Type": "application/x-www-form-urlencoded"},
                data={"grant_type": "client_credentials",
                      "scope": "https://api.ebay.com/oauth/api_scope"},
                timeout=20,
            )
            resp.raise_for_status()
            return resp.json().get("access_token")
        except Exception:
            return None

    def search(self, query: str, limit: int = 3) -> list[dict[str, Any]]:  # pragma: no cover
        import httpx

        token = self._token()
        if not token:
            return MockPartsProvider().search(query, limit)  # degrade gracefully
        env = _ENDPOINTS.get(settings.ebay_env, _ENDPOINTS["production"])
        try:
            resp = httpx.get(
                env["browse"],
                headers={"Authorization": f"Bearer {token}",
                         "X-EBAY-C-MARKETPLACE-ID": settings.ebay_marketplace},
                params={"q": query, "limit": min(max(1, limit), 10)},
                timeout=20,
            )
            resp.raise_for_status()
            summaries = resp.json().get("itemSummaries", []) or []
        except Exception:
            return MockPartsProvider().search(query, limit)
        items = []
        for it in summaries[:limit]:
            price = it.get("price") or {}
            img = (it.get("image") or {}).get("imageUrl")
            items.append({
                "title": it.get("title"),
                "price": float(price.get("value")) if price.get("value") else None,
                "currency": price.get("currency", "GBP"),
                "condition": it.get("condition"),
                "url": it.get("itemWebUrl") or _ebay_search_url(query),
                "image": img,
                "source": EBAY_SOURCE,
            })
        return items
