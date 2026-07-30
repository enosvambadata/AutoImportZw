"""Parse a pasted vehicle listing into structured fields.

The dealer pastes listing text they already have; Claude extracts the details (make, model, mileage,
damage, category, etc.) into a structured shape that pre-fills the appraisal form. When no Anthropic
key is configured, a best-effort heuristic parser is used instead. This reads pasted text only — it
never fetches from a third-party site.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ..core.config import settings

_MAKES = [
    "Ford", "Vauxhall", "Volkswagen", "VW", "BMW", "Audi", "Mercedes", "Mercedes-Benz", "Toyota",
    "Nissan", "Kia", "Hyundai", "Honda", "Peugeot", "Citroen", "Renault", "Seat", "Skoda", "Mazda",
    "Mini", "Land Rover", "Jaguar", "Volvo", "Fiat", "Suzuki", "Dacia", "Tesla", "Mitsubishi",
    # Commercial / van makes (IAA & Copart list plenty of these)
    "Iveco", "Maxus", "LDV", "Isuzu", "MAN", "DAF", "Scania", "Fuso",
]

LISTING_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "make": {"type": ["string", "null"]},
        "model": {"type": ["string", "null"]},
        "derivative": {"type": ["string", "null"]},
        "model_year": {"type": ["integer", "null"]},
        "mileage": {"type": ["integer", "null"]},
        "colour": {"type": ["string", "null"]},
        "fuel_type": {"type": ["string", "null"]},
        "transmission": {"type": ["string", "null"]},
        "category_marker": {"type": ["string", "null"], "enum": ["N", "S", "A", "B", None]},
        "runner_status": {"type": ["string", "null"], "enum": ["RUNNER", "NON_RUNNER", "UNKNOWN", None]},
        "guide_price": {"type": ["number", "null"]},
        "lot_number": {"type": ["string", "null"]},
        "description": {"type": ["string", "null"]},
        "damage_summary": {"type": ["string", "null"]},
        "damage_items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "area": {"type": "string"},
                    "description": {"type": "string"},
                    "severity": {"type": "string", "enum": ["MINOR", "MODERATE", "SEVERE", "UNKNOWN"]},
                },
                "required": ["area", "description", "severity"],
            },
        },
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["make", "model", "derivative", "model_year", "mileage", "colour", "fuel_type",
                 "transmission", "category_marker", "runner_status", "guide_price", "lot_number",
                 "description", "damage_summary", "damage_items", "warnings"],
}

SYSTEM_PROMPT = (
    "You extract structured details from a UK vehicle auction/sales listing that a dealer has pasted. "
    "Use ONLY information stated in the text — never invent values; use null when a field is not "
    "present. mileage and guide_price are numbers only (strip units and £). category_marker is the "
    "insurance write-off category if stated (N/S/A/B). runner_status: 'spares or repairs'/'non-runner' "
    "-> NON_RUNNER; 'starts and drives'/'runner' -> RUNNER; else UNKNOWN. Copy the seller's free-text "
    "description (condition, MOT, history, extras, faults) verbatim into 'description'. Summarise any "
    "damage and list individual damage points with a severity. Return only the requested fields."
)


def _claude_parse(text: str) -> dict[str, Any]:
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1500,
        output_config={"format": {"type": "json_schema", "schema": LISTING_SCHEMA}},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Listing:\n\n{text[:8000]}"}],
    )
    body = "".join(b.text for b in message.content if getattr(b, "type", None) == "text")
    data = json.loads(body)
    data["source"] = "CLAUDE"
    return data


def _num(match: re.Match | None) -> int | None:
    if not match:
        return None
    raw = match.group(1).replace(",", "")
    try:
        return int(float(raw))
    except ValueError:
        return None


def _heuristic_parse(text: str) -> dict[str, Any]:
    t = text.strip()
    low = t.lower()

    make = next((m for m in _MAKES if re.search(rf"\b{re.escape(m.lower())}\b", low)), None)
    year = _num(re.search(r"\b(19[89]\d|20[0-4]\d)\b", t))
    # Mileage: IAA labels it "Odometer" (often "Unverified <n>"); others say "<n> miles".
    mileage = (_num(re.search(r"([\d,]{3,7})\s*(?:miles|mi\b)", low))
               or _num(re.search(r"(?:mileage|odometer)[^\d]{0,40}([\d,]{4,7})", low)))

    # Model + derivative: IAA titles read "<year> <make> <model> <derivative...> <NNNN>cc <fuel>...".
    model = derivative = None
    if make:
        mm = re.search(rf"\b{re.escape(make)}\b\s+([A-Za-z0-9][\w .\-/]*?)\s+\d{{3,4}}\s*cc",
                       t, re.IGNORECASE)
        if mm:
            phrase = " ".join(mm.group(1).split())
            model, _, derivative = phrase.partition(" ")
            derivative = derivative or None
    price = None
    pm = re.search(r"£\s*([\d,]+(?:\.\d+)?)", t)
    if pm:
        try:
            price = float(pm.group(1).replace(",", ""))
        except ValueError:
            price = None

    cat = None
    cm = re.search(r"cat(?:egory)?\.?\s*([nsab])\b", low)
    if cm:
        cat = cm.group(1).upper()

    # Seller description: the free-text block IAA/SYNETIQ put under a "Description" heading.
    description = None
    dm = re.search(r"description\s*\n+(.+?)(?:\n\s*seller details|\n\s*seller\b|$)",
                   t, re.IGNORECASE | re.DOTALL)
    if dm:
        description = " ".join(dm.group(1).split()).strip() or None

    runner = "UNKNOWN"
    if any(w in low for w in ("non-runner", "non runner", "spares or repairs", "spares/repairs")):
        runner = "NON_RUNNER"
    elif any(w in low for w in ("starts and drives", "runs and drives", "runner", "drives well")):
        runner = "RUNNER"

    lot = None
    lm = re.search(r"\blot(?:\s*(?:no|number|#))?[:.\s]*([a-z0-9-]{4,12})\b", low)
    if lm:
        lot = lm.group(1).upper()

    fuel = next((f for f in ("diesel", "petrol", "hybrid", "electric") if f in low), None)
    trans = ("Automatic" if "automatic" in low or re.search(r"\bauto\b", low)
             else "Manual" if "manual" in low else None)

    return {
        "source": "HEURISTIC",
        "make": make, "model": model, "derivative": derivative, "model_year": year,
        "mileage": mileage, "colour": None, "fuel_type": (fuel.title() if fuel else None),
        "transmission": trans, "category_marker": cat, "runner_status": runner,
        "guide_price": price, "lot_number": lot, "description": description,
        "damage_summary": None, "damage_items": [], "warnings": [],
    }


def parse_listing(text: str) -> dict[str, Any]:
    if settings.claude_vision_enabled:
        try:
            return _claude_parse(text)
        except Exception:
            pass  # degrade to heuristic rather than fail
    return _heuristic_parse(text)
