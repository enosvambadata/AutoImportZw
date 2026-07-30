"""Deterministic mock adapters.

Responses are seeded from the registration string so the same input always yields the same
output (repeatable demos/tests). Every payload is labelled ``data_source = MOCK_ADAPTER`` and
must never be presented as coming from a real named provider.
"""

from __future__ import annotations

import hashlib
from datetime import date, timedelta
from typing import Any

MOCK_SOURCE = "MOCK_ADAPTER"

_MAKES = ["Ford", "Vauxhall", "Volkswagen", "BMW", "Audi", "Toyota", "Nissan", "Kia"]
_MODELS = {
    "Ford": ["Fiesta", "Focus", "Kuga"],
    "Vauxhall": ["Corsa", "Astra", "Mokka"],
    "Volkswagen": ["Golf", "Polo", "Tiguan"],
    "BMW": ["1 Series", "3 Series", "X1"],
    "Audi": ["A3", "A4", "Q3"],
    "Toyota": ["Yaris", "Corolla", "RAV4"],
    "Nissan": ["Micra", "Qashqai", "Juke"],
    "Kia": ["Ceed", "Sportage", "Picanto"],
}


def _seed(reg: str) -> int:
    return int(hashlib.sha256(reg.upper().encode()).hexdigest(), 16)


class MockVehicleIdentityProvider:
    name = "mock-identity"

    def lookup(self, registration: str) -> dict[str, Any] | None:
        if not registration:
            return None
        s = _seed(registration)
        make = _MAKES[s % len(_MAKES)]
        model = _MODELS[make][(s // 7) % len(_MODELS[make])]
        year = 2013 + (s // 13) % 11
        return {
            "registration": registration.upper(),
            "make": make,
            "model": model,
            "model_year": year,
            "registration_date": date(year, 3 + (s % 9), 1 + (s % 27)).isoformat(),
            "fuel_type": ["Petrol", "Diesel", "Hybrid"][s % 3],
            "transmission": ["Manual", "Automatic"][(s // 3) % 2],
            "engine_size": [1000, 1200, 1400, 1600, 2000][(s // 5) % 5],
            "colour": ["Black", "White", "Grey", "Blue", "Red"][(s // 11) % 5],
            "euro_status": "6" if year >= 2016 else "5",
            "ulez_compliant": year >= 2016,
            "data_source": MOCK_SOURCE,
        }


class MockMotHistoryProvider:
    name = "mock-mot"

    def history(self, registration: str) -> dict[str, Any] | None:
        if not registration:
            return None
        s = _seed(registration)
        fails = s % 3
        passes = 3 + s % 5
        base_odo = 40000 + s % 60000
        tests = []
        for i in range(passes):
            year_off = passes - i
            tests.append({
                "date": (date.today() - timedelta(days=365 * year_off)).isoformat(),
                "result": "PASSED",
                "odometer": base_odo + i * (6000 + s % 3000),
                "unit": "MI",
                "expiry": (date.today() - timedelta(days=365 * year_off - 365)).isoformat(),
                "advisories": (s + i) % 3,
                "dangerous": 0,
            })
        return {
            "mot_expiry": (date.today() + timedelta(days=30 + s % 300)).isoformat(),
            "mot_tests": list(reversed(tests)),
            "mot_pass_count": passes,
            "mot_fail_count": fails,
            "advisory_count": s % 6,
            "major_defect_count": s % 2,
            "dangerous_defect_count": 1 if s % 17 == 0 else 0,
            "repeated_failures": s % 11 == 0,
            "data_source": MOCK_SOURCE,
        }


class MockVehicleHistoryProvider:
    name = "mock-history"

    def check(self, registration: str, vin: str | None = None) -> dict[str, Any] | None:
        if not registration:
            return None
        s = _seed(registration)
        return {
            "finance_marker": s % 23 == 0,
            "stolen_marker": s % 97 == 0,
            "write_off_marker": s % 29 == 0,
            "mileage_discrepancy": s % 19 == 0,
            "plate_changes": s % 3,
            "keeper_changes": 1 + s % 5,
            "service_history_status": ["FULL", "PARTIAL", "NONE"][s % 3],
            "data_source": MOCK_SOURCE,
        }


class MockValuationProvider:
    name = "mock-valuation"

    def valuation(self, *, make: str, model: str, year: int, mileage: int) -> dict[str, Any]:
        base = 16000 - (2025 - year) * 1100 - (mileage // 1000) * 45
        base = max(1200, base)
        return {
            "cap_clean": round(base * 0.92),
            "cap_average": round(base * 0.85),
            "cap_below": round(base * 0.78),
            "estimated_retail": round(base * 1.08),
            "data_source": MOCK_SOURCE,
        }


class MockMarketComparablesProvider:
    name = "mock-comparables"

    def comparables(self, *, make: str, model: str, year: int,
                    mileage: int, limit: int = 5) -> list[dict[str, Any]]:
        seed = _seed(f"{make}{model}{year}")
        base = max(1500, 16500 - (2025 - year) * 1050 - (mileage // 1000) * 42)
        out = []
        for i in range(limit):
            jitter = ((seed >> (i * 3)) % 1400) - 700
            out.append({
                "source": MOCK_SOURCE,
                "listing_reference": f"MK-{seed % 100000}-{i}",
                "asking_price": round(base + jitter + i * 120),
                "mileage": mileage + ((seed >> i) % 8000) - 4000,
                "year": year,
                "trim": f"{model} SE",
                "distance_miles": 5 + (seed >> i) % 180,
                "seller_type": ["Franchise", "Independent", "Private"][(seed >> i) % 3],
                "days_listed": (seed >> i) % 60,
            })
        return out


class MockAuctionListingProvider:
    name = "mock-auction"

    def catalogue(self, auction_house: str) -> list[dict[str, Any]]:
        # Placeholder catalogue — a real feed requires a commercial agreement.
        return []
