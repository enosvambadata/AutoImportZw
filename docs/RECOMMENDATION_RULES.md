# Recommendation Rules

Implemented in `apps/api/app/services/recommendation.py`. This is a **transparent rules engine, not
machine learning.** Every result returns the decision plus reasons, positive factors, warnings,
missing information, a recommended next action and a confidence level.

## Inputs

`expected_profit`, `pessimistic_profit`, `target_profit`, `roi_on_cost`, `min_roi`, `risk_level`,
`critical_flags`, `policy_blocks`, `history_warnings`, `market_confidence`, `estimated_days_to_sell`,
`current_bid`, `absolute_max_bid`, `guide_price`, `missing_fields`, `max_acceptable_pessimistic_loss`,
`strong_buy_multiplier` (default 1.25).

## Decision ladder (first match wins)

1. **INCOMPLETE_DATA** — any required valuation field missing. Confidence forced to LOW.
2. **PASS** — current bid > absolute max; **or** (cold evaluation only) guide price > absolute max;
   **or** a critical history flag (stolen / outstanding finance); **or** a dealership policy block;
   **or** expected profit ≤ 0.
3. **HIGH_RISK** — pessimistic loss below `max_acceptable_pessimistic_loss` (default −£500); **or**
   expected profit meets target but risk is High/Critical.
4. **STRONG_BUY** — expected profit ≥ `1.25 × target`, pessimistic profit > 0, ROI ≥ threshold,
   risk Low/Medium, no critical flag.
5. **BUY** — expected profit ≥ target, ROI ≥ threshold, risk not High/Critical, no critical flag.
6. **CONSIDER** — otherwise (positive but below target, ROI below threshold, or moderate confidence).

### Note on the guide-price PASS

Guide-above-absolute forces a PASS only when evaluating a lot **cold** (no live `current_bid`). Once a
live bid below the absolute max exists, the guide is context, not a blocker — otherwise every good buy
whose guide sits between safe and absolute would be wrongly rejected.

## Blocking flags

`stolen` and `outstanding_finance` are **critical** and block BUY/STRONG_BUY by default (they route to
PASS). Category N/S vehicles are **flagged** but never auto-rejected — that is dealership policy
(`allow_category_n`, `allow_category_s`), surfaced as a `policy_block` when disallowed.

## Confidence

Derived from `market_confidence`, downgraded when data is missing or risk is High/Critical. Returns
LOW / MEDIUM / HIGH.

## Tests

`apps/api/tests/test_recommendation.py` covers every outcome (STRONG_BUY, BUY, CONSIDER, HIGH_RISK,
PASS, INCOMPLETE_DATA) and each blocking path. The seed dataset intentionally produces a spread across
all outcomes.
