"""Transparent, rules-based recommendation engine.

This is deliberately NOT machine learning. Every decision returns the plain-English reasons,
positive factors, warnings, missing information, a recommended next action and a confidence
level, so a dealer can see exactly why the system said what it said.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from ..calculations.money import to_decimal
from .risk import RiskLevel


class Recommendation(str, Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    CONSIDER = "CONSIDER"
    HIGH_RISK = "HIGH_RISK"
    PASS = "PASS"
    INCOMPLETE_DATA = "INCOMPLETE_DATA"


class Confidence(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class RecommendationInputs:
    expected_profit: Decimal
    pessimistic_profit: Decimal
    target_profit: Decimal
    roi_on_cost: Decimal | None
    min_roi: Decimal
    risk_level: RiskLevel
    critical_flags: list[str] = field(default_factory=list)
    policy_blocks: list[str] = field(default_factory=list)
    history_warnings: list[str] = field(default_factory=list)
    market_confidence: Confidence = Confidence.MEDIUM
    estimated_days_to_sell: int = 45
    current_bid: Decimal | None = None
    absolute_max_bid: Decimal | None = None
    guide_price: Decimal | None = None
    missing_fields: list[str] = field(default_factory=list)
    max_acceptable_pessimistic_loss: Decimal = Decimal("-500")
    strong_buy_multiplier: Decimal = Decimal("1.25")


@dataclass
class RecommendationResult:
    decision: Recommendation
    reasons: list[str]
    positive_factors: list[str]
    warning_factors: list[str]
    missing_information: list[str]
    next_action: str
    confidence: Confidence

    def to_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "reasons": self.reasons,
            "positive_factors": self.positive_factors,
            "warning_factors": self.warning_factors,
            "missing_information": self.missing_information,
            "next_action": self.next_action,
            "confidence": self.confidence.value,
        }


def _confidence(inp: RecommendationInputs) -> Confidence:
    score = {Confidence.LOW: 0, Confidence.MEDIUM: 1, Confidence.HIGH: 2}[inp.market_confidence]
    if inp.missing_fields:
        score -= 1
    if inp.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
        score -= 1
    if score <= 0:
        return Confidence.LOW
    if score == 1:
        return Confidence.MEDIUM
    return Confidence.HIGH


def recommend(inp: RecommendationInputs) -> RecommendationResult:
    exp = to_decimal(inp.expected_profit)
    pes = to_decimal(inp.pessimistic_profit)
    target = to_decimal(inp.target_profit)
    roi = inp.roi_on_cost
    positives: list[str] = []
    warnings: list[str] = []
    reasons: list[str] = []

    # Build shared factor lists first.
    if exp >= target:
        positives.append(f"Expected profit £{exp} meets or exceeds the £{target} target")
    if pes > 0:
        positives.append(f"Even the pessimistic case is profitable (£{pes})")
    if roi is not None and roi >= inp.min_roi:
        positives.append(f"Return on cash ({roi:.1%}) meets the {inp.min_roi:.0%} minimum")
    if inp.risk_level in (RiskLevel.LOW, RiskLevel.MEDIUM):
        positives.append(f"Risk level is {inp.risk_level.value.lower()}")

    for flag in inp.critical_flags:
        warnings.append(flag)
    for w in inp.history_warnings:
        warnings.append(w)
    if inp.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
        warnings.append(f"Overall risk is {inp.risk_level.value.lower()}")
    if pes < 0:
        warnings.append(f"Pessimistic case loses £{abs(pes)}")
    if inp.estimated_days_to_sell >= 75:
        warnings.append(f"Expected to take ~{inp.estimated_days_to_sell} days to sell")

    confidence = _confidence(inp)

    # ---- Decision ladder (first match wins) ----

    # 1. Incomplete data.
    if inp.missing_fields:
        reasons.append("Required appraisal values are missing, so a reliable recommendation "
                       "cannot be produced.")
        return RecommendationResult(
            Recommendation.INCOMPLETE_DATA, reasons, positives, warnings,
            inp.missing_fields,
            "Complete the missing fields, then recalculate.",
            Confidence.LOW,
        )

    # 2. Hard PASS conditions.
    if inp.current_bid is not None and inp.absolute_max_bid is not None \
            and to_decimal(inp.current_bid) > to_decimal(inp.absolute_max_bid):
        reasons.append(f"The current bid (£{to_decimal(inp.current_bid)}) is above the absolute "
                       f"maximum (£{to_decimal(inp.absolute_max_bid)}).")
        return RecommendationResult(
            Recommendation.PASS, reasons, positives, warnings, [],
            "Stop bidding — the price now erodes your target profit.", confidence)

    # Guide-above-absolute only forces a PASS when evaluating a lot cold. If a live current bid
    # is present and already below the absolute maximum, the guide is just context, not a blocker.
    if inp.current_bid is None and inp.guide_price is not None \
            and inp.absolute_max_bid is not None \
            and to_decimal(inp.guide_price) > to_decimal(inp.absolute_max_bid):
        reasons.append(f"The guide price (£{to_decimal(inp.guide_price)}) already exceeds the "
                       f"absolute maximum bid (£{to_decimal(inp.absolute_max_bid)}).")
        return RecommendationResult(
            Recommendation.PASS, reasons, positives, warnings, [],
            "Skip this lot unless it sells well below guide.", confidence)

    if inp.critical_flags:
        reasons.append("A critical history flag is present: " + "; ".join(inp.critical_flags) + ".")
        return RecommendationResult(
            Recommendation.PASS, reasons, positives, warnings, [],
            "Do not buy until the critical marker is fully resolved in writing.", confidence)

    if inp.policy_blocks:
        reasons.append("The vehicle fails dealership purchasing policy: "
                       + "; ".join(inp.policy_blocks) + ".")
        return RecommendationResult(
            Recommendation.PASS, reasons, positives, warnings, [],
            "Override requires an administrator to change dealership policy.", confidence)

    if exp <= 0:
        reasons.append(f"Expected profit is non-positive (£{exp}) at the reference price.")
        return RecommendationResult(
            Recommendation.PASS, reasons, positives, warnings, [],
            "Only revisit if the hammer price falls below break-even.", confidence)

    # 3. HIGH_RISK — profitable but risky, or a large pessimistic loss.
    if pes < inp.max_acceptable_pessimistic_loss:
        reasons.append(f"The pessimistic loss (£{pes}) breaches the acceptable floor "
                       f"(£{to_decimal(inp.max_acceptable_pessimistic_loss)}).")
        return RecommendationResult(
            Recommendation.HIGH_RISK, reasons, positives, warnings, [],
            "Only proceed after a physical/mechanical inspection reduces the downside.",
            confidence)

    if exp >= target and inp.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
        reasons.append(f"Expected profit meets target, but overall risk is "
                       f"{inp.risk_level.value.lower()}.")
        return RecommendationResult(
            Recommendation.HIGH_RISK, reasons, positives, warnings, [],
            "Inspect in person and confirm repair costs before bidding to your maximum.",
            confidence)

    # 4. STRONG_BUY.
    roi_ok = roi is not None and roi >= inp.min_roi
    if (exp >= target * inp.strong_buy_multiplier and pes > 0 and roi_ok
            and inp.risk_level in (RiskLevel.LOW, RiskLevel.MEDIUM)):
        reasons.append(f"Expected profit (£{exp}) beats target by ≥25%, the pessimistic case is "
                       f"still profitable, ROI clears the threshold and risk is acceptable.")
        return RecommendationResult(
            Recommendation.STRONG_BUY, reasons, positives, warnings, [],
            "Bid with confidence up to your safe maximum.", confidence)

    # 5. BUY.
    if exp >= target and roi_ok and inp.risk_level != RiskLevel.CRITICAL \
            and inp.risk_level != RiskLevel.HIGH:
        reasons.append(f"Expected profit meets the £{target} target with acceptable ROI and risk.")
        return RecommendationResult(
            Recommendation.BUY, reasons, positives, warnings, [],
            "Bid up to your safe maximum; hold at the absolute maximum.", confidence)

    # 6. CONSIDER (positive but below target, or moderate confidence).
    reasons.append(f"Expected profit (£{exp}) is positive but below the £{target} target "
                   f"or confidence is only moderate.")
    return RecommendationResult(
        Recommendation.CONSIDER, reasons, positives, warnings, [],
        "Worth a low bid near the safe maximum, or improve the data and re-run.",
        confidence)
