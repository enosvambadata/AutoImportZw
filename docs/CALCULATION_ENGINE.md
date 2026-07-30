# Calculation Engine

The engine lives in `apps/api/app/calculations/` and is **pure, deterministic and framework-free**
(depends only on the stdlib `decimal`). It is the single source of truth for every monetary figure;
the frontend never re-implements these formulas — it renders values from `POST /api/v1/appraisals/preview`
and the persisted `result_snapshot`.

## Money rules

- All arithmetic uses `Decimal`. Floats are routed through `str()` to avoid binary error.
- Money rounds to **2 dp, ROUND_HALF_UP** (`money()`); ratios round to 4 dp (`ratio()`).
- Division guards against zero (`safe_div` returns `None`).

## Fee strategies (`fees.py`)

A `FeeSchedule` is a list of `FeeBand`s plus VAT settings. A fee is a pure function of the hammer:

```
raw_fee(h) = fixed_fee + percentage * h   (clamped to [minimum_fee, maximum_fee])
```

Bands carry an optional `[lower_bound, upper_bound)` range so **tiered** fees select the band that
contains the hammer price (first match wins). VAT can be **added** (`stated_inclusive=false`) or
**decomposed** from a VAT-inclusive figure (`stated_inclusive=true`). Supported shapes: fixed,
percentage, percentage+fixed, tiered, min/max caps, VAT on the fee, VAT-inclusive/exclusive input.

## Inputs (`AppraisalInputs`)

Sale prices (expected/conservative/optimistic), expected discount, a list of `CostRange`
(estimated/min/max non-bid costs), the `FeeSchedule`, and policy: `target_profit`, `risk_reserve`
(full recommended), `mandatory_min_reserve`, `min_roi`, plus context (`current_bid`, `guide_price`,
`above_absolute_delta`, `estimated_days_to_sell`, `holding_cost_per_day`).

### Reference hammer

Headline profit is anchored at a **reference hammer**, chosen as: live `current_bid` → auction
`guide_price` → the safe max bid. This answers the dealer's real question: *"if I win at this price,
what do I make?"*

## Bid solving

For a scenario with net sale `S` (sale − discount), fixed costs `C` and a deduction `D`:

```
g(h) = S − C − D − (h + fee(h))
```

`h + fee(h)` is monotonically increasing, so the root (where `g = 0`) is found by **bisection**
between `0` and `S − C − D` (tolerance £0.005; returns `0` if the target can't be met at any hammer).
This handles fees that depend on the hammer price — including tier crossings — without per-shape algebra.

| Bid | Scenario | Deduction `D` |
|-----|----------|---------------|
| **Safe maximum** | pessimistic (conservative sale, max costs) | `risk_reserve + target_profit` |
| **Absolute maximum** | expected (expected sale, est costs) | `mandatory_min_reserve + target_profit` |
| **Break-even** | expected | `0` |

Consequences (also asserted in tests): pessimistic profit at the safe max = `target + reserve`;
expected profit at the absolute max = `target + mandatory_min_reserve`; ordering
`safe ≤ absolute ≤ break_even`.

## Profit scenarios

Deterministic bands from the user's own ranges (never random / ML):

- **Pessimistic** — conservative sale − discount, max-end costs.
- **Expected** — expected sale − discount, estimated costs.
- **Optimistic** — optimistic sale − half discount, min-end costs.

`expected_profit = net_sale − (hammer + fee(hammer) + costs)` at the reference hammer.

## ROI & margin

- **ROI on cost** = expected_profit / total_cash_invested (hammer + fee + costs).
- **ROI on hammer** = expected_profit / hammer.
- **Margin** = expected_profit / net_sale. All labelled explicitly in the UI.

## Bid ladder

Outcomes at: current bid (if any), safe max, safe/absolute midpoint, absolute max, and a configurable
amount above absolute. Each rung shows cash required, expected profit, worst-case profit, ROI, margin
and an `exceeds_absolute` flag.

## Sensitivity matrix

Expected profit as selling price varies −15%…+10% (rows) against preparation cost −10%…+50%
(columns), plus 1-D arrays for days-to-sell (via `holding_cost_per_day`) and customer discount.

## VAT scope note

VAT on the **buyer fee** is modelled explicitly. VAT on the **vehicle sale margin** (VAT-margin scheme)
depends on the realised sale price rather than the bid, so it is intentionally out of scope for the
bid calculation for the MVP and documented here and in `ASSUMPTIONS.md`.

## Tests

`apps/api/tests/test_fees.py` and `test_engine.py` cover fixed/percentage/tiered/VAT fees, tier
boundaries, zero/negative profit, high repair costs, iterative fee solving, scenario ordering, ROI,
rounding, the bid ladder and sensitivity shape.
