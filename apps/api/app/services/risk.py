"""Configurable weighted risk scoring (0-100) across 12 factors.

Pure and deterministic. Weights are dealership-configurable; sensible defaults are provided.
Critical hard flags (stolen / outstanding finance) are surfaced separately and are used by the
recommendation engine to block a BUY. Category markers are *flagged* but never auto-reject —
that is dealership policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from ..calculations.money import to_decimal


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


DEFAULT_WEIGHTS: dict[str, float] = {
    "mechanical": 1.4,
    "bodywork": 1.1,
    "history": 1.5,
    "market_demand": 1.0,
    "pricing_confidence": 1.2,
    "age": 0.7,
    "mileage": 0.9,
    "ownership_history": 0.8,
    "mot": 1.2,
    "depreciation": 0.7,
    "liquidity": 1.0,
    "documentation": 0.9,
}

CATEGORY_LABELS = {
    "mechanical": "Mechanical",
    "bodywork": "Bodywork / structural",
    "history": "Vehicle history",
    "market_demand": "Market demand",
    "pricing_confidence": "Pricing confidence",
    "age": "Age",
    "mileage": "Mileage",
    "ownership_history": "Ownership history",
    "mot": "MOT",
    "depreciation": "Depreciation",
    "liquidity": "Liquidity / days to sell",
    "documentation": "Documentation",
}


@dataclass
class RiskInputs:
    # History / legal
    category_marker: str | None = None  # e.g. "N", "S", "B", "A"
    stolen_marker: bool = False
    outstanding_finance: bool = False
    write_off_marker: bool = False
    mileage_discrepancy: bool = False
    imported: bool = False
    plate_changes: int = 0
    keeper_changes: int = 0
    # MOT
    mot_fail_count: int = 0
    dangerous_defect_count: int = 0
    major_defect_count: int = 0
    repeated_mot_failures: bool = False
    # Condition / mechanical
    non_runner: bool = False
    condition_grade: int | None = None  # 1 (best) .. 5 (worst)
    repair_uncertainty_ratio: Decimal = Decimal("0")  # (max-min prep)/estimated
    # Docs
    missing_service_history: bool = False
    one_key_only: bool = False
    # Market / valuation
    unusually_low_market_price: bool = False
    comparable_count: int = 3
    valuation_gap_ratio: Decimal = Decimal("0")  # (optimistic-conservative)/expected
    # Vehicle facts
    age_years: Decimal | None = None
    mileage: int | None = None
    estimated_days_to_sell: int = 45
    # Policy
    allow_category_n: bool = True
    allow_category_s: bool = False


@dataclass
class RiskResult:
    scores: dict[str, int]
    weighted_total: int
    level: RiskLevel
    explanations: list[str]
    warning_flags: list[str]
    critical_flags: list[str]
    suggested_risk_reserve: Decimal
    policy_blocks: list[str]

    def to_dict(self) -> dict:
        return {
            "scores": self.scores,
            "weighted_total": self.weighted_total,
            "level": self.level.value,
            "explanations": self.explanations,
            "warning_flags": self.warning_flags,
            "critical_flags": self.critical_flags,
            "suggested_risk_reserve": str(self.suggested_risk_reserve),
            "policy_blocks": self.policy_blocks,
        }


def _cap(x: float) -> int:
    return int(max(0, min(100, round(x))))


def level_for(score: int) -> RiskLevel:
    if score <= 24:
        return RiskLevel.LOW
    if score <= 49:
        return RiskLevel.MEDIUM
    if score <= 69:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL


def assess(inp: RiskInputs, weights: dict[str, float] | None = None) -> RiskResult:
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    s: dict[str, int] = {}
    explanations: list[str] = []
    warnings: list[str] = []
    critical: list[str] = []
    policy_blocks: list[str] = []

    # --- mechanical ---
    mech = 0.0
    if inp.non_runner:
        mech += 55
        warnings.append("Vehicle is a non-runner")
    mech += float(inp.dangerous_defect_count) * 20
    ru = float(to_decimal(inp.repair_uncertainty_ratio))
    mech += min(35, ru * 70)
    if ru >= 0.4:
        warnings.append("High uncertainty in repair estimate")
    s["mechanical"] = _cap(mech)

    # --- bodywork / structural ---
    body = 0.0
    cat = (inp.category_marker or "").upper().strip()
    if cat in ("S", "A", "B"):
        body += 60
        warnings.append(f"Insurance category {cat} (structural) marker")
    elif cat == "N":
        body += 35
        warnings.append("Insurance category N (non-structural) marker")
    if inp.condition_grade is not None and inp.condition_grade >= 4:
        body += 25
        warnings.append("Poor condition grade")
    s["bodywork"] = _cap(body)

    # --- history ---
    hist = 0.0
    if inp.stolen_marker:
        hist += 100
        critical.append("Recorded as stolen")
    if inp.outstanding_finance:
        hist += 80
        critical.append("Outstanding finance recorded")
    if inp.write_off_marker:
        hist += 30
    if inp.mileage_discrepancy:
        hist += 45
        warnings.append("Mileage discrepancy detected")
    if inp.imported:
        hist += 15
    hist += min(15, inp.plate_changes * 5)
    s["history"] = _cap(hist)

    # --- market demand ---
    market = 0.0
    if inp.unusually_low_market_price:
        market += 35
        warnings.append("Market asking prices are unusually low")
    if inp.comparable_count <= 1:
        market += 45
    elif inp.comparable_count == 2:
        market += 25
    s["market_demand"] = _cap(market)

    # --- pricing confidence ---
    pricing = 0.0
    gap = float(to_decimal(inp.valuation_gap_ratio))
    pricing += min(60, gap * 200)  # a 30% gap -> 60
    if gap >= 0.25:
        warnings.append("Wide gap between optimistic and conservative valuations")
    if inp.comparable_count <= 2:
        pricing += 20
    if inp.comparable_count <= 1:
        warnings.append("Very limited comparable vehicles")
    s["pricing_confidence"] = _cap(pricing)

    # --- age ---
    age = 0.0
    if inp.age_years is not None:
        ay = float(to_decimal(inp.age_years))
        age = min(90, max(0, (ay - 3) * 9))  # 3y ~0, 13y ~90
    s["age"] = _cap(age)

    # --- mileage (relative to age) ---
    mile = 0.0
    if inp.mileage is not None and inp.age_years is not None and float(to_decimal(inp.age_years)) > 0:
        per_year = inp.mileage / float(to_decimal(inp.age_years))
        mile = min(90, max(0, (per_year - 10000) / 120))  # 22k/yr -> 100 pre-cap
        if per_year > 18000:
            warnings.append("High mileage relative to age")
    elif inp.mileage is not None and inp.mileage > 120000:
        mile = 60
    s["mileage"] = _cap(mile)

    # --- ownership history ---
    own = min(80, inp.keeper_changes * 12)
    if inp.keeper_changes >= 6:
        warnings.append("Many previous keepers")
    s["ownership_history"] = _cap(own)

    # --- MOT ---
    mot = 0.0
    mot += min(45, inp.mot_fail_count * 12)
    mot += inp.dangerous_defect_count * 25
    mot += inp.major_defect_count * 8
    if inp.repeated_mot_failures:
        mot += 20
        warnings.append("Repeated MOT failures for the same issue")
    if inp.dangerous_defect_count > 0:
        warnings.append("Dangerous MOT defect(s) recorded")
    s["mot"] = _cap(mot)

    # --- depreciation ---
    dep = 0.0
    if inp.age_years is not None:
        ay = float(to_decimal(inp.age_years))
        dep = min(70, max(0, (ay - 4) * 8))
    s["depreciation"] = _cap(dep)

    # --- liquidity / days to sell ---
    liq = min(90, max(0, (inp.estimated_days_to_sell - 30) * 1.5))
    if inp.estimated_days_to_sell >= 75:
        warnings.append("Expected to be slow to sell")
    s["liquidity"] = _cap(liq)

    # --- documentation ---
    docs = 0.0
    if inp.missing_service_history:
        docs += 40
        warnings.append("Missing service history")
    if inp.one_key_only:
        docs += 25
        warnings.append("Only one key supplied")
    if inp.imported:
        docs += 20
        warnings.append("Imported vehicle — documentation may differ")
    s["documentation"] = _cap(docs)

    # --- weighted total ---
    total_w = sum(w[k] for k in s)
    weighted = sum(w[k] * s[k] for k in s) / total_w if total_w else 0
    weighted_total = _cap(weighted)
    level = level_for(weighted_total)

    # Explanations for the top contributors.
    ranked = sorted(s.items(), key=lambda kv: w[kv[0]] * kv[1], reverse=True)
    for key, val in ranked[:4]:
        if val > 0:
            explanations.append(f"{CATEGORY_LABELS[key]} risk scored {val}/100")

    # Policy blocks (highlighted, not automatic PASS unless configured).
    if cat == "N" and not inp.allow_category_n:
        policy_blocks.append("Dealership policy: Category N vehicles are not permitted")
    if cat in ("S", "A", "B") and not inp.allow_category_s:
        policy_blocks.append("Dealership policy: Category S/structural vehicles are not permitted")

    # Suggested reserve scales with risk (Decimal, rounded to £10).
    reserve = Decimal(weighted_total) / Decimal("100") * Decimal("600") + Decimal("100")
    reserve = (reserve / Decimal("10")).to_integral_value() * Decimal("10")

    return RiskResult(
        scores=s,
        weighted_total=weighted_total,
        level=level,
        explanations=explanations,
        warning_flags=warnings,
        critical_flags=critical,
        suggested_risk_reserve=reserve,
        policy_blocks=policy_blocks,
    )
