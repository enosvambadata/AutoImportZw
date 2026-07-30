"""CSV catalogue import: parse, map source headers, validate, and convert to normalised listings.

Designed for a dealer importing **their own account's export** (e.g. a SYNETIQ or Copart catalogue
download) — not scraping. Source-specific column aliases map each provider's export headers onto our
canonical fields; the committed rows flow through the same ingestion pipeline as the API connectors,
so imported data is fully first-class (and re-importing updates rather than duplicates).
"""

from __future__ import annotations

import csv
import io
import re
from decimal import Decimal
from typing import Any

from ..integrations.connectors.base import NormalizedListing

TEMPLATE_COLUMNS = [
    "registration", "vin", "make", "model", "trim", "year", "mileage", "fuel",
    "transmission", "auction_house", "auction_date", "lot_number", "guide_price",
    "cap_clean", "cap_average", "cap_below", "category", "condition_grade",
    "runner_status", "vat_status", "notes",
]

REQUIRED = ["make", "model"]

# Canonical field -> accepted source header variants (lowercased). Covers SYNETIQ / Copart /
# generic export wording so a dealer's own download maps without manual fiddling.
ALIASES: dict[str, list[str]] = {
    "registration": ["registration", "reg", "vrm", "reg no", "reg number", "plate", "number plate"],
    "vin": ["vin", "chassis", "chassis number", "chassis no", "vin number"],
    "make": ["make", "manufacturer", "marque"],
    "model": ["model"],
    "trim": ["trim", "derivative", "variant", "spec", "grade name"],
    "year": ["year", "reg year", "registration year", "year of manufacture", "model year",
             "manufacture year", "yom"],
    "mileage": ["mileage", "odometer", "miles", "odometer reading", "mileage (miles)"],
    "fuel": ["fuel", "fuel type"],
    "transmission": ["transmission", "gearbox"],
    "auction_house": ["auction_house", "auction house", "auction", "site", "location", "branch",
                      "centre", "yard", "depot"],
    "auction_date": ["auction_date", "auction date", "sale date", "sale", "date", "auction datetime",
                     "sale datetime"],
    "lot_number": ["lot_number", "lot", "lot number", "lot no", "lot no.", "stock number",
                   "stock no", "reference", "ref"],
    "guide_price": ["guide_price", "guide", "guide price", "reserve", "reserve price", "estimate",
                    "cap guide", "start price", "starting bid"],
    "cap_clean": ["cap_clean", "cap clean", "clean"],
    "cap_average": ["cap_average", "cap average", "average", "cap avg"],
    "cap_below": ["cap_below", "cap below", "below"],
    "category": ["category", "damage category", "cat", "insurance category", "salvage category",
                 "loss category"],
    "condition_grade": ["condition_grade", "condition grade", "grade", "condition"],
    "runner_status": ["runner_status", "runner", "runner status", "starts", "start status",
                      "drivable", "runs", "starts & drives"],
    "vat_status": ["vat_status", "vat", "vat status", "vat qualifying"],
    "notes": ["notes", "comments", "remarks", "description", "damage notes"],
}

# Import profiles set the provenance label and a sensible default auction-house name.
PROFILES: dict[str, dict[str, str]] = {
    "generic": {"source": "CSV_IMPORT", "default_house": "CSV import"},
    "synetiq": {"source": "SYNETIQ", "default_house": "SYNETIQ"},
    "copart": {"source": "COPART", "default_house": "Copart"},
}

_HEADER_TO_CANONICAL = {v: canon for canon, variants in ALIASES.items() for v in variants}


def template_csv() -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(TEMPLATE_COLUMNS)
    writer.writerow([
        "AB12CDE", "", "Ford", "Focus", "Titanium", "2019", "42000", "Petrol",
        "Manual", "SYNETIQ", "2026-08-01T10:00", "L142", "8250",
        "8600", "8100", "7600", "N", "2", "RUNNER", "MARGIN", "Drives well",
    ])
    return buf.getvalue()


def _canonical(header: str) -> str:
    h = header.strip().lower()
    return _HEADER_TO_CANONICAL.get(h, h)


def _num(value: str | None) -> float | None:
    value = (value or "").strip().replace(",", "").replace("£", "")
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _category(value: str | None) -> str | None:
    if not value:
        return None
    m = re.search(r"\b([NSAB])\b", value.upper())
    return m.group(1) if m else None


def _runner(value: str | None) -> str | None:
    v = (value or "").strip().lower()
    if not v:
        return None
    if any(t in v for t in ("non", "no", "spares", "not")):
        return "NON_RUNNER"
    if any(t in v for t in ("runner", "start", "drives", "runs", "yes")):
        return "RUNNER"
    return "UNKNOWN"


def parse_and_validate(content: str, profile: str = "generic") -> dict[str, Any]:
    """Parse CSV text, map source headers to canonical fields, validate and flag duplicates."""
    reader = csv.DictReader(io.StringIO(content))
    raw_headers = [h.strip() for h in (reader.fieldnames or []) if h]
    mapped = {h: _canonical(h) for h in raw_headers}
    unknown = [h for h, c in mapped.items() if c not in TEMPLATE_COLUMNS]

    rows: list[dict[str, Any]] = []
    seen_keys: dict[str, int] = {}
    valid_count = 0

    for idx, raw in enumerate(reader, start=1):
        record: dict[str, str] = {}
        for k, v in raw.items():
            if k is None:
                continue
            record[_canonical(k)] = (v or "").strip()
        errors: list[str] = []

        for req in REQUIRED:
            if not record.get(req):
                errors.append(f"Missing required field '{req}'")

        year = record.get("year")
        if year and (_num(year) is None or not (1950 <= int(_num(year)) <= 2100)):
            errors.append("Year is not a valid 4-digit year")
        if record.get("mileage") and _num(record["mileage"]) is None:
            errors.append("Mileage is not numeric")
        for money_field in ("guide_price", "cap_clean", "cap_average", "cap_below"):
            if record.get(money_field) and _num(record[money_field]) is None:
                errors.append(f"{money_field} is not numeric")
        grade = record.get("condition_grade")
        if grade and _num(grade) is not None and not (1 <= int(_num(grade)) <= 5):
            errors.append("condition_grade must be 1-5")

        dup_key = (record.get("registration") or record.get("vin")
                   or f"{record.get('make')}|{record.get('model')}|{record.get('lot_number')}").upper()
        is_duplicate = dup_key in seen_keys
        if not is_duplicate:
            seen_keys[dup_key] = idx
        if not errors and not is_duplicate:
            valid_count += 1

        rows.append({
            "row": idx, "data": record, "errors": errors,
            "is_duplicate": is_duplicate, "importable": not errors and not is_duplicate,
        })

    return {
        "profile": profile,
        "headers": [mapped[h] for h in raw_headers],
        "unknown_columns": unknown,
        "rows": rows,
        "summary": {
            "total": len(rows),
            "valid": valid_count,
            "with_errors": sum(1 for r in rows if r["errors"]),
            "duplicates": sum(1 for r in rows if r["is_duplicate"]),
        },
    }


def _dec(value: str | None) -> Decimal | None:
    n = _num(value)
    return Decimal(str(n)) if n is not None else None


def to_normalized_listings(parsed: dict[str, Any], profile: str = "generic",
                          default_auction_house: str | None = None) -> list[NormalizedListing]:
    """Convert the importable rows of a parsed result into NormalizedListing objects."""
    prof = PROFILES.get(profile, PROFILES["generic"])
    source = prof["source"]
    fallback_house = default_auction_house or prof["default_house"]

    out: list[NormalizedListing] = []
    for i, row in enumerate(parsed["rows"]):
        if not row["importable"]:
            continue
        d = row["data"]
        year = _num(d.get("year"))
        mileage = _num(d.get("mileage"))
        grade = _num(d.get("condition_grade"))
        out.append(NormalizedListing(
            source=source,
            auction_house_name=d.get("auction_house") or fallback_house,
            lot_number=d.get("lot_number") or f"IMP-{i + 1}",
            make=d["make"], model=d["model"],
            registration=d.get("registration") or None,
            vin=d.get("vin") or None,
            derivative=d.get("trim") or None,
            model_year=int(year) if year is not None else None,
            mileage=int(mileage) if mileage is not None else None,
            fuel_type=d.get("fuel") or None,
            transmission=d.get("transmission") or None,
            category_marker=_category(d.get("category")),
            auction_datetime_iso=d.get("auction_date") or None,
            guide_price=_dec(d.get("guide_price")),
            cap_clean=_dec(d.get("cap_clean")),
            cap_average=_dec(d.get("cap_average")),
            cap_below=_dec(d.get("cap_below")),
            condition_grade=int(grade) if grade is not None else None,
            runner_status=_runner(d.get("runner_status")),
            vat_status=(d.get("vat_status") or "MARGIN").upper()[:20],
            notes=d.get("notes") or None,
        ))
    return out
