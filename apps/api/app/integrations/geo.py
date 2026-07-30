"""Geo helper backed by postcodes.io (free, no API key).

Turns UK postcodes into coordinates so the app can compute real distances — dealer to auction site
(for transport-cost estimates) and to market comparables. The haversine maths is pure and unit-tested;
only ``geocode`` touches the network.
"""

from __future__ import annotations

import math
from typing import Any

POSTCODES_IO = "https://api.postcodes.io/postcodes"
EARTH_RADIUS_MILES = 3958.8


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/long points, in miles."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2)
    return 2 * EARTH_RADIUS_MILES * math.asin(min(1.0, math.sqrt(a)))


def geocode(postcode: str) -> dict[str, Any] | None:
    """Look up a UK postcode via postcodes.io. Returns lat/long + region, or None if invalid."""
    import httpx

    pc = (postcode or "").strip()
    if not pc:
        return None
    try:
        resp = httpx.get(f"{POSTCODES_IO}/{pc}", timeout=15)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        r = resp.json().get("result") or {}
    except Exception:
        return None
    if r.get("latitude") is None or r.get("longitude") is None:
        return None
    return {
        "postcode": r.get("postcode"),
        "latitude": r["latitude"],
        "longitude": r["longitude"],
        "region": r.get("region"),
        "admin_district": r.get("admin_district"),
    }


def distance_between(origin: str, destination: str) -> float | None:
    """Road-agnostic straight-line distance in miles between two postcodes (None if either invalid)."""
    a = geocode(origin)
    b = geocode(destination)
    if not a or not b:
        return None
    return round(haversine_miles(a["latitude"], a["longitude"],
                                 b["latitude"], b["longitude"]), 1)


def estimate_transport(miles: float, floor: float = 45.0, per_mile: float = 0.95) -> float:
    """Rough one-way trade transport estimate: a base cost plus a per-mile rate, with a floor."""
    return round(max(floor, floor + miles * per_mile), 2)
