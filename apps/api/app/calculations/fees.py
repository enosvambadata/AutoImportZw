"""Auction buyer-fee strategies.

Fees are configurable per auction house via one or more :class:`FeeBand` rows. We never
hard-code a single auction house's commercial table. A fee is a pure function of the
hammer price; VAT on the fee is modelled as a separate, explicit line.

Supported shapes (any combination via bands):
- Fixed fee
- Percentage of hammer price
- Percentage + fixed
- Tiered fee (band selected by hammer price range)
- Minimum / maximum fee caps
- VAT on the buyer fee (rate configurable)
- VAT-inclusive or VAT-exclusive stated fee
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .money import ZERO, money, to_decimal


@dataclass(frozen=True)
class FeeBand:
    """A single fee rule, optionally applying only within a hammer-price tier.

    ``lower_bound`` inclusive, ``upper_bound`` exclusive (``None`` = unbounded).
    The applicable band is the one whose range contains the hammer price. If bands
    overlap, the first matching band (in list order) wins.
    """

    fixed_fee: Decimal = ZERO
    percentage: Decimal = ZERO  # e.g. Decimal("0.075") for 7.5%
    minimum_fee: Decimal | None = None
    maximum_fee: Decimal | None = None
    lower_bound: Decimal | None = None
    upper_bound: Decimal | None = None

    def contains(self, hammer: Decimal) -> bool:
        if self.lower_bound is not None and hammer < self.lower_bound:
            return False
        if self.upper_bound is not None and hammer >= self.upper_bound:
            return False
        return True

    def raw_fee(self, hammer: Decimal) -> Decimal:
        fee = self.fixed_fee + (self.percentage * hammer)
        if self.minimum_fee is not None and fee < self.minimum_fee:
            fee = self.minimum_fee
        if self.maximum_fee is not None and fee > self.maximum_fee:
            fee = self.maximum_fee
        return fee


@dataclass(frozen=True)
class FeeResult:
    net: Decimal  # fee excluding VAT
    vat: Decimal  # VAT on the fee
    gross: Decimal  # net + vat

    @property
    def total(self) -> Decimal:
        return self.gross


@dataclass
class FeeSchedule:
    """A resolved fee schedule for one auction house.

    :param bands: ordered fee bands; the first band containing the hammer price is used.
        For a single flat rule, pass one unbounded band.
    :param vat_applicable: whether VAT is added to the buyer fee.
    :param vat_rate: VAT rate (default 0.20).
    :param stated_inclusive: if ``True``, the band fee already includes VAT and is
        decomposed into net + VAT; if ``False`` the fee is ex-VAT and VAT is added.
    """

    bands: list[FeeBand] = field(default_factory=list)
    vat_applicable: bool = True
    vat_rate: Decimal = Decimal("0.20")
    stated_inclusive: bool = False

    def _band_for(self, hammer: Decimal) -> FeeBand:
        for band in self.bands:
            if band.contains(hammer):
                return band
        # No matching band -> zero fee (documented behaviour).
        return FeeBand()

    def compute(self, hammer: Decimal | str | int | float) -> FeeResult:
        hammer = to_decimal(hammer)
        if hammer < 0:
            hammer = ZERO
        raw = self._band_for(hammer).raw_fee(hammer)

        if not self.vat_applicable:
            return FeeResult(net=money(raw), vat=ZERO, gross=money(raw))

        rate = self.vat_rate
        if self.stated_inclusive:
            net = raw / (Decimal("1") + rate)
            vat = raw - net
        else:
            net = raw
            vat = raw * rate
        return FeeResult(net=money(net), vat=money(vat), gross=money(net + vat))


# ---- Convenience constructors -------------------------------------------------

def flat_percentage(pct: Decimal, minimum: Decimal | None = None,
                    maximum: Decimal | None = None, **kw) -> FeeSchedule:
    return FeeSchedule(bands=[FeeBand(percentage=pct, minimum_fee=minimum,
                                      maximum_fee=maximum)], **kw)


def fixed(amount: Decimal, **kw) -> FeeSchedule:
    return FeeSchedule(bands=[FeeBand(fixed_fee=amount)], **kw)


def percentage_plus_fixed(pct: Decimal, fixed_amount: Decimal, **kw) -> FeeSchedule:
    return FeeSchedule(bands=[FeeBand(percentage=pct, fixed_fee=fixed_amount)], **kw)
