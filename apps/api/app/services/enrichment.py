"""Apply a registration look-up to a vehicle so the data feeds the risk engine.

Writes identity fields onto the vehicle and the MOT/history record onto its VehicleHistory, then the
risk engine (which reads VehicleHistory) automatically reflects MOT fails, advisories and dangerous
defects. Uses whichever providers are active (DVLA/DVSA when configured, else mock).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from ..integrations import get_providers
from ..models.catalogue import Vehicle, VehicleHistory

_IDENTITY_FIELDS = ("make", "model", "model_year", "fuel_type", "transmission",
                    "engine_size", "colour")
_MOT_FIELDS = ("mot_pass_count", "mot_fail_count", "advisory_count", "major_defect_count",
               "dangerous_defect_count", "repeated_failures")
_HISTORY_FIELDS = ("finance_marker", "stolen_marker", "write_off_marker", "mileage_discrepancy",
                   "plate_changes", "keeper_changes", "service_history_status")


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def enrich_vehicle(vehicle: Vehicle, *, force: bool = False) -> dict[str, Any]:
    """Look up the vehicle's registration and apply identity + MOT + history to it in place."""
    reg = vehicle.registration
    if not reg:
        return {"applied": False, "reason": "no_registration"}

    p = get_providers()
    identity = p.identity.lookup(reg)
    mot = p.mot.history(reg)
    hist = p.history.check(reg)

    if identity:
        for field in _IDENTITY_FIELDS:
            val = identity.get(field)
            if val not in (None, "") and (force or not getattr(vehicle, field)):
                setattr(vehicle, field, val)

    if vehicle.history is None:
        vehicle.history = VehicleHistory(vehicle_id=vehicle.id)
    h = vehicle.history

    if mot:
        for field in _MOT_FIELDS:
            if mot.get(field) is not None:
                setattr(h, field, mot[field])
        expiry = _parse_date(mot.get("mot_expiry"))
        if expiry:
            h.mot_expiry = expiry
        if mot.get("mot_tests") is not None:
            h.mot_tests = mot["mot_tests"]
    if hist:
        for field in _HISTORY_FIELDS:
            if hist.get(field) is not None:
                setattr(h, field, hist[field])

    provenance = (mot or {}).get("data_source") or (identity or {}).get("data_source") or "MOCK_ADAPTER"
    h.history_provider = provenance
    h.data_retrieved_at = datetime.now(timezone.utc)

    return {
        "applied": True,
        "identity": bool(identity),
        "mot": bool(mot),
        "history": bool(hist),
        "provenance": provenance,
    }
