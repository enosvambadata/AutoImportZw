"""Official UK government vehicle-data adapters (DVLA VES, DVSA MOT History).

These are the sanctioned, free APIs for registration look-ups. They activate only when their
credentials are configured; otherwise the mock adapters are used. Real HTTP calls are wrapped so a
failure degrades to the mock rather than breaking the look-up.

Response field mappings follow the documented API shapes — verify them against a live response when
you first connect (portals occasionally adjust field names).
"""

from __future__ import annotations

from typing import Any

from ..core.config import settings

DVLA_SOURCE = "DVLA_VES"
DVSA_SOURCE = "DVSA_MOT"


class DvlaVesIdentityProvider:
    """DVLA Vehicle Enquiry Service — make, year, fuel, colour, engine (no model)."""

    name = "dvla-ves"

    def lookup(self, registration: str) -> dict[str, Any] | None:  # pragma: no cover - needs key
        import httpx

        reg = (registration or "").upper().replace(" ", "")
        if not reg:
            return None
        try:
            resp = httpx.post(
                settings.dvla_ves_url,
                headers={"x-api-key": settings.dvla_ves_api_key,
                         "Content-Type": "application/json"},
                json={"registrationNumber": reg},
                timeout=20,
            )
            resp.raise_for_status()
            d = resp.json()
        except Exception:
            return None
        return {
            "registration": d.get("registrationNumber", reg),
            "make": d.get("make"),
            "model": None,  # VES does not return model; DVSA MOT supplies it
            "model_year": d.get("yearOfManufacture"),
            "fuel_type": d.get("fuelType"),
            "colour": d.get("colour"),
            "engine_size": d.get("engineCapacity"),
            "euro_status": None,
            "tax_status": d.get("taxStatus"),
            "mot_status": d.get("motStatus"),
            "data_source": DVLA_SOURCE,
        }


class DvsaMotHistoryProvider:
    """DVSA MOT History — make, model, colour, fuel and full MOT test history (OAuth2 + API key)."""

    name = "dvsa-mot"

    def _token(self) -> str | None:  # pragma: no cover - needs creds
        import httpx

        try:
            resp = httpx.post(
                settings.dvsa_mot_token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": settings.dvsa_mot_client_id,
                    "client_secret": settings.dvsa_mot_client_secret,
                    "scope": settings.dvsa_mot_scope,
                },
                timeout=20,
            )
            resp.raise_for_status()
            return resp.json().get("access_token")
        except Exception:
            return None

    def history(self, registration: str) -> dict[str, Any] | None:  # pragma: no cover - needs creds
        import httpx

        reg = (registration or "").upper().replace(" ", "")
        token = self._token()
        if not reg or not token:
            return None
        try:
            resp = httpx.get(
                f"{settings.dvsa_mot_url}/{reg}",
                headers={"Authorization": f"Bearer {token}",
                         "X-API-Key": settings.dvsa_mot_api_key},
                timeout=20,
            )
            resp.raise_for_status()
            v = resp.json()
        except Exception:
            return None

        tests = v.get("motTests", []) or []
        passes = sum(1 for t in tests if str(t.get("testResult", "")).upper() in ("PASS", "PASSED"))
        fails = sum(1 for t in tests if str(t.get("testResult", "")).upper() in ("FAIL", "FAILED"))
        dangerous = 0
        advisories = 0
        for t in tests:
            for r in t.get("rfrAndComments", []) or []:
                kind = str(r.get("type", "")).upper()
                if kind == "DANGEROUS":
                    dangerous += 1
                elif kind == "ADVISORY":
                    advisories += 1
        latest_expiry = next((t.get("expiryDate") for t in tests if t.get("expiryDate")), None)

        mot_tests = []
        for t in tests:
            rfr = t.get("rfrAndComments", []) or []
            mot_tests.append({
                "date": str(t.get("completedDate") or "")[:10] or None,
                "result": str(t.get("testResult") or "").upper() or None,
                "odometer": t.get("odometerValue"),
                "unit": t.get("odometerUnit"),
                "expiry": t.get("expiryDate"),
                "advisories": sum(1 for r in rfr if str(r.get("type", "")).upper() == "ADVISORY"),
                "dangerous": sum(1 for r in rfr if str(r.get("type", "")).upper() == "DANGEROUS"),
            })
        year = v.get("manufactureYear")
        if not year:
            for k in ("firstUsedDate", "manufactureDate", "registrationDate"):
                val = str(v.get(k) or "")
                if val[:4].isdigit():
                    year = int(val[:4])
                    break
        return {
            "make": v.get("make"),
            "model": v.get("model"),
            "model_year": year,
            "colour": v.get("primaryColour"),
            "fuel_type": v.get("fuelType"),
            "mot_expiry": latest_expiry,
            "mot_tests": mot_tests,
            "mot_pass_count": passes,
            "mot_fail_count": fails,
            "advisory_count": advisories,
            "dangerous_defect_count": dangerous,
            "data_source": DVSA_SOURCE,
        }
