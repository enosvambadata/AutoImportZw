"""Deterministic demo catalogue connector.

Always available (no credentials). Produces clearly-labelled DEMO listings so the ingestion
pipeline and everything downstream can be exercised end-to-end before a real provider is connected.
"""

from __future__ import annotations

from decimal import Decimal

from .base import NormalizedListing

_DEMO = [
    ("Ford", "Fiesta", "ST-Line", "MA19DEM", 2019, 38000, "Petrol", "Manual", None, 6100, 5200),
    ("Volkswagen", "Golf", "Match TSI", "MB18DEM", 2018, 51000, "Petrol", "Manual", None, 8300, 6900),
    ("Nissan", "Qashqai", "N-Connecta", "MC17DEM", 2017, 62000, "Diesel", "Manual", "N", 7200, 5600),
    ("BMW", "3 Series", "320d M Sport", "MD17DEM", 2017, 74000, "Diesel", "Automatic", None, 11500, 8700),
]


class DemoCatalogueConnector:
    name = "demo"
    source = "DEMO"

    def is_configured(self) -> bool:
        return True

    def fetch_listings(self, *, since_iso: str | None = None,
                       limit: int = 200) -> list[NormalizedListing]:
        out: list[NormalizedListing] = []
        for i, (make, model, deriv, reg, year, mileage, fuel, trans, cat, retail, guide) in \
                enumerate(_DEMO[:limit]):
            out.append(NormalizedListing(
                source="DEMO",
                auction_house_name="Demo Salvage & Auction",
                lot_number=f"DEMO-{100 + i}",
                make=make, model=model, derivative=deriv, registration=reg,
                model_year=year, mileage=mileage, fuel_type=fuel, transmission=trans,
                colour="Grey", category_marker=cat,
                guide_price=Decimal(guide), cap_average=Decimal(int(retail * 0.9)),
                cap_clean=Decimal(int(retail * 0.97)), estimated_retail=Decimal(retail),
                condition_grade=3 if cat else 2,
                runner_status="RUNNER", vat_status="MARGIN",
                notes="Demonstration catalogue data (not from a real provider).",
            ))
        return out
