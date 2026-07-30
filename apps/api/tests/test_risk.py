"""Risk-scoring tests: bands, hard flags, category policy, suggested reserve."""

from decimal import Decimal

from app.services.risk import RiskInputs, RiskLevel, assess, level_for


def test_clean_vehicle_is_low_risk():
    r = assess(RiskInputs(age_years=Decimal("3"), mileage=30000, comparable_count=6,
                          condition_grade=2, estimated_days_to_sell=30))
    assert r.level in (RiskLevel.LOW, RiskLevel.MEDIUM)
    assert not r.critical_flags


def test_stolen_is_critical_flag():
    r = assess(RiskInputs(stolen_marker=True))
    assert "Recorded as stolen" in r.critical_flags
    assert r.scores["history"] == 100


def test_outstanding_finance_is_critical_flag():
    r = assess(RiskInputs(outstanding_finance=True))
    assert any("finance" in c.lower() for c in r.critical_flags)


def test_level_boundaries():
    assert level_for(0) is RiskLevel.LOW
    assert level_for(24) is RiskLevel.LOW
    assert level_for(25) is RiskLevel.MEDIUM
    assert level_for(49) is RiskLevel.MEDIUM
    assert level_for(50) is RiskLevel.HIGH
    assert level_for(69) is RiskLevel.HIGH
    assert level_for(70) is RiskLevel.CRITICAL
    assert level_for(100) is RiskLevel.CRITICAL


def test_category_n_flagged_but_not_blocked_when_allowed():
    r = assess(RiskInputs(category_marker="N", allow_category_n=True))
    assert any("category N" in w for w in r.warning_flags)
    assert not r.policy_blocks


def test_category_n_blocked_when_policy_forbids():
    r = assess(RiskInputs(category_marker="N", allow_category_n=False))
    assert r.policy_blocks


def test_category_s_blocked_by_default():
    r = assess(RiskInputs(category_marker="S"))
    assert r.policy_blocks


def test_non_runner_and_dangerous_defects_raise_mechanical_and_mot():
    r = assess(RiskInputs(non_runner=True, dangerous_defect_count=2))
    assert r.scores["mechanical"] >= 50
    assert r.scores["mot"] >= 50
    assert any("non-runner" in w.lower() for w in r.warning_flags)


def test_mileage_discrepancy_warning():
    r = assess(RiskInputs(mileage_discrepancy=True))
    assert any("mileage discrepancy" in w.lower() for w in r.warning_flags)


def test_high_risk_increases_suggested_reserve():
    low = assess(RiskInputs(age_years=Decimal("2"), mileage=10000, comparable_count=8))
    high = assess(RiskInputs(non_runner=True, category_marker="S", missing_service_history=True,
                             mot_fail_count=3, dangerous_defect_count=2, comparable_count=1))
    assert high.suggested_risk_reserve > low.suggested_risk_reserve


def test_custom_weights_change_total():
    base = RiskInputs(non_runner=True)
    default = assess(base)
    heavy = assess(base, weights={"mechanical": 5.0})
    assert heavy.weighted_total >= default.weighted_total
