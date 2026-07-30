"""Fee-strategy unit tests, including tier boundaries, VAT and caps."""

from decimal import Decimal

import pytest

from app.calculations.fees import (
    FeeBand,
    FeeSchedule,
    fixed,
    flat_percentage,
    percentage_plus_fixed,
)


def D(x):
    return Decimal(str(x))


def test_fixed_fee_no_vat():
    sched = fixed(D("250"), vat_applicable=False)
    r = sched.compute(D("5000"))
    assert r.net == D("250.00")
    assert r.vat == D("0.00")
    assert r.gross == D("250.00")


def test_fixed_fee_with_vat():
    sched = fixed(D("250"), vat_applicable=True, vat_rate=D("0.20"))
    r = sched.compute(D("5000"))
    assert r.net == D("250.00")
    assert r.vat == D("50.00")
    assert r.gross == D("300.00")


def test_percentage_fee():
    sched = flat_percentage(D("0.075"), vat_applicable=False)
    r = sched.compute(D("4000"))
    assert r.net == D("300.00")  # 7.5% of 4000


def test_percentage_fee_with_minimum_applies():
    sched = flat_percentage(D("0.05"), minimum=D("200"), vat_applicable=False)
    r = sched.compute(D("1000"))  # 5% = 50, floored to 200
    assert r.net == D("200.00")


def test_percentage_fee_with_maximum_caps():
    sched = flat_percentage(D("0.10"), maximum=D("500"), vat_applicable=False)
    r = sched.compute(D("20000"))  # 10% = 2000, capped to 500
    assert r.net == D("500.00")


def test_percentage_plus_fixed():
    sched = percentage_plus_fixed(D("0.05"), D("60"), vat_applicable=False)
    r = sched.compute(D("2000"))  # 100 + 60
    assert r.net == D("160.00")


def test_vat_inclusive_decomposition():
    # A £300 VAT-inclusive fee decomposes to £250 net + £50 VAT at 20%.
    sched = fixed(D("300"), vat_applicable=True, vat_rate=D("0.20"), stated_inclusive=True)
    r = sched.compute(D("5000"))
    assert r.net == D("250.00")
    assert r.vat == D("50.00")
    assert r.gross == D("300.00")


def test_tiered_fee_boundaries():
    # Tier 1: [0, 5000) -> £200 ; Tier 2: [5000, 10000) -> £350 ; Tier 3: [10000, inf) -> £500
    sched = FeeSchedule(
        vat_applicable=False,
        bands=[
            FeeBand(fixed_fee=D("200"), lower_bound=None, upper_bound=D("5000")),
            FeeBand(fixed_fee=D("350"), lower_bound=D("5000"), upper_bound=D("10000")),
            FeeBand(fixed_fee=D("500"), lower_bound=D("10000"), upper_bound=None),
        ],
    )
    assert sched.compute(D("4999.99")).net == D("200.00")
    assert sched.compute(D("5000")).net == D("350.00")  # boundary is inclusive lower
    assert sched.compute(D("9999.99")).net == D("350.00")
    assert sched.compute(D("10000")).net == D("500.00")


def test_no_matching_band_is_zero():
    sched = FeeSchedule(
        vat_applicable=False,
        bands=[FeeBand(fixed_fee=D("200"), lower_bound=D("1000"), upper_bound=D("2000"))],
    )
    assert sched.compute(D("50")).net == D("0.00")


def test_negative_hammer_treated_as_zero():
    sched = flat_percentage(D("0.10"), vat_applicable=False)
    assert sched.compute(D("-100")).net == D("0.00")


@pytest.mark.parametrize(
    "hammer,expected_net",
    [(D("0"), D("0.00")), (D("100"), D("10.00")), (D("1234.56"), D("123.46"))],
)
def test_percentage_rounding_half_up(hammer, expected_net):
    sched = flat_percentage(D("0.10"), vat_applicable=False)
    assert sched.compute(hammer).net == expected_net
