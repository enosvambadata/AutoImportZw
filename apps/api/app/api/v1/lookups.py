"""Data-provider lookups (mock adapters). Responses are labelled MOCK_ADAPTER."""

from __future__ import annotations

from fastapi import APIRouter, Query

from ...core.deps import CurrentUser
from ...integrations import get_providers
from ...integrations.connectors import get_valuation_connector

router = APIRouter(prefix="/lookups", tags=["lookups"])


@router.get("/registration")
async def registration_lookup(user: CurrentUser, reg: str = Query(min_length=1)):
    p = get_providers()
    identity = p.identity.lookup(reg)
    mot = p.mot.history(reg)
    history = p.history.check(reg)

    # DVLA VES has no model; fill it (and any gaps) from the DVSA MOT record. When the MOT record is
    # official (DVSA), its make/model/etc. are authoritative and override a mock identity.
    if identity and mot:
        mot_official = mot.get("data_source") == "DVSA_MOT"
        for field in ("model", "make", "model_year", "colour", "fuel_type"):
            if mot.get(field) and (mot_official or not identity.get(field)):
                identity[field] = mot[field]

    official = any(
        (d or {}).get("data_source") in ("DVLA_VES", "DVSA_MOT")
        for d in (identity, mot)
    )
    return {
        "identity": identity,
        "mot": mot,
        "history": history,
        "provenance": "DVLA_DVSA" if official else "MOCK_ADAPTER",
        "disclaimer": ("Official DVLA/DVSA data." if official else
                       "Demonstration data from a mock adapter — not from any real provider."),
    }


@router.get("/valuation")
async def valuation_lookup(user: CurrentUser, make: str, model: str, year: int, mileage: int):
    p = get_providers()
    comparables = p.comparables.comparables(make=make, model=model, year=year, mileage=mileage)

    # Use the Auto Trader connector for live retail pricing when it is configured; else the mock.
    autotrader = get_valuation_connector("autotrader")
    if autotrader is not None and autotrader.is_configured():
        valuation = autotrader.valuation_dict(make=make, model=model, year=year, mileage=mileage)
        return {"valuation": valuation, "comparables": comparables,
                "provenance": "AUTO_TRADER",
                "disclaimer": "Live retail pricing via Auto Trader Connect."}

    return {
        "valuation": p.valuation.valuation(make=make, model=model, year=year, mileage=mileage),
        "comparables": comparables,
        "provenance": "MOCK_ADAPTER",
        "disclaimer": "Demonstration data from a mock adapter — not sourced from any real provider.",
    }
