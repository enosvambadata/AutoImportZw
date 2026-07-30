"""Zimbabwe (ZIMRA) import-duty calculation for imported vehicles.

Method (per ZIMRA "Calculation of duty on importation of private motor vehicles"):
  VDP (Value for Duty Purposes) = CIF = vehicle value + freight + insurance to the port of entry,
                                  plus clearing incidentals.
  Customs Duty = duty_rate x VDP          (duty_rate depends on vehicle category — see table)
  Surtax       = SURTAX_RATE x VDP        (ONLY passenger-type vehicles older than 5 years)
  VAT          = VAT_RATE x (VDP + Customs Duty)     [ZIMRA VTP base = VDP + duty]

The category rates below are ASSUMPTIONS for an estimate — Zimbabwe's schedule varies by body type,
engine size, payload/GVM and age, and the final assessment is always ZIMRA's. Sources disagree on
some figures; these are the commonly-cited passenger/commercial rates.

Sources (checked 2026-07):
  - ZIMRA: zimra.co.zw/customs (calculation of duty on private motor vehicles)
  - zimtax.co.zw, payecalculator.co.zw/zimra-duty-rates-2026, deepbeez.com, carused.jp
Notes: some 2026 sources cite VAT at 15.5% (up from 15%) — change VAT_RATE if confirmed for the entry.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

SURTAX_RATE = Decimal("0.35")   # passenger vehicle > 5 years old
VAT_RATE = Decimal("0.15")
SURTAX_AGE_THRESHOLD = 5

# category -> (label, customs-duty rate, whether surtax can apply)
VEHICLE_CATEGORIES: dict[str, dict] = {
    "CAR": {"label": "Passenger car (sedan / hatch / wagon)", "duty": Decimal("0.40"), "surtax": True},
    "SUV": {"label": "SUV / 4x4", "duty": Decimal("0.60"), "surtax": True},
    "DOUBLE_CAB": {"label": "Double cab", "duty": Decimal("0.60"), "surtax": False},
    "SINGLE_CAB": {"label": "Single cab / pickup", "duty": Decimal("0.40"), "surtax": False},
    "LIGHT_TRUCK": {"label": "Light truck / lorry (GVM < 5t)", "duty": Decimal("0.40"), "surtax": False},
    "HEAVY_TRUCK": {"label": "Heavy truck (GVM ≥ 5t)", "duty": Decimal("0.25"), "surtax": False},
}
DEFAULT_CATEGORY = "CAR"


def _q(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def list_categories() -> list[dict]:
    return [{"key": k, "label": v["label"], "duty_rate": str(v["duty"]), "surtax": v["surtax"]}
            for k, v in VEHICLE_CATEGORIES.items()]


def zim_duty(vdp: Decimal | float | str, *, category: str = DEFAULT_CATEGORY,
             vehicle_age_years: int | None = None,
             surtax_applies: bool | None = None) -> dict[str, Decimal | str]:
    """Return customs duty, surtax and VAT for a Value-for-Duty (VDP) amount in USD, by category."""
    profile = VEHICLE_CATEGORIES.get(category, VEHICLE_CATEGORIES[DEFAULT_CATEGORY])
    vdp = Decimal(str(vdp))

    if surtax_applies is None:
        surtax_applies = bool(profile["surtax"]) and (
            vehicle_age_years is not None and vehicle_age_years > SURTAX_AGE_THRESHOLD)

    customs_duty = _q(vdp * profile["duty"])
    surtax = _q(vdp * SURTAX_RATE) if surtax_applies else Decimal("0.00")
    vat = _q((vdp + customs_duty) * VAT_RATE)
    return {
        "category": category if category in VEHICLE_CATEGORIES else DEFAULT_CATEGORY,
        "duty_rate": str(profile["duty"]),
        "vdp": _q(vdp),
        "customs_duty": customs_duty,
        "surtax": surtax,
        "vat": vat,
        "total_taxes": _q(customs_duty + surtax + vat),
    }
