"""Recommendation-engine tests: every outcome and each blocking flag."""

from decimal import Decimal

from app.services.recommendation import (
    Confidence,
    Recommendation,
    RecommendationInputs,
    recommend,
)
from app.services.risk import RiskLevel


def D(x):
    return Decimal(str(x))


def make(**kw) -> RecommendationInputs:
    base = dict(
        expected_profit=D("1500"),
        pessimistic_profit=D("400"),
        target_profit=D("1200"),
        roi_on_cost=D("0.20"),
        min_roi=D("0.15"),
        risk_level=RiskLevel.LOW,
        market_confidence=Confidence.HIGH,
    )
    base.update(kw)
    return RecommendationInputs(**base)


def test_strong_buy():
    r = recommend(make(expected_profit=D("1600"), pessimistic_profit=D("500")))
    assert r.decision is Recommendation.STRONG_BUY
    assert r.positive_factors


def test_buy():
    # Meets target but not by 25% -> BUY not STRONG_BUY.
    r = recommend(make(expected_profit=D("1250"), pessimistic_profit=D("200")))
    assert r.decision is Recommendation.BUY


def test_consider_below_target():
    r = recommend(make(expected_profit=D("800"), pessimistic_profit=D("100"),
                       risk_level=RiskLevel.MEDIUM))
    assert r.decision is Recommendation.CONSIDER


def test_high_risk_when_meets_target_but_high_risk():
    r = recommend(make(expected_profit=D("1600"), risk_level=RiskLevel.HIGH))
    assert r.decision is Recommendation.HIGH_RISK


def test_high_risk_when_pessimistic_loss_too_large():
    r = recommend(make(expected_profit=D("1600"), pessimistic_profit=D("-900"),
                       max_acceptable_pessimistic_loss=D("-500")))
    assert r.decision is Recommendation.HIGH_RISK


def test_pass_when_expected_non_positive():
    r = recommend(make(expected_profit=D("-100")))
    assert r.decision is Recommendation.PASS


def test_pass_when_bid_exceeds_absolute():
    r = recommend(make(current_bid=D("9000"), absolute_max_bid=D("8000")))
    assert r.decision is Recommendation.PASS
    assert "absolute maximum" in " ".join(r.reasons).lower()


def test_pass_when_guide_above_absolute():
    r = recommend(make(guide_price=D("9000"), absolute_max_bid=D("8000")))
    assert r.decision is Recommendation.PASS


def test_pass_on_critical_flag():
    r = recommend(make(critical_flags=["Recorded as stolen"]))
    assert r.decision is Recommendation.PASS


def test_pass_on_policy_block():
    r = recommend(make(policy_blocks=["Category S not permitted"]))
    assert r.decision is Recommendation.PASS


def test_incomplete_data():
    r = recommend(make(missing_fields=["expected_retail_price", "auction_house"]))
    assert r.decision is Recommendation.INCOMPLETE_DATA
    assert r.missing_information == ["expected_retail_price", "auction_house"]
    assert r.confidence is Confidence.LOW


def test_every_result_has_next_action_and_reasons():
    r = recommend(make())
    assert r.next_action
    assert r.reasons
