# Assumptions & Documented Defaults

Where the brief left a decision open, we chose a production-oriented default and recorded it here.

## Money & rounding
- All monetary maths uses Python `Decimal`. Money is rounded to **2 dp, ROUND_HALF_UP**.
- Percentages/ratios (ROI, margin) are computed at full precision and rounded for display only (4 dp).
- Currency is **GBP** throughout; formatting uses `en-GB`.

## VAT
- Default VAT rate is **20%**. Stored as dealership-configurable (`vat_rate`).
- VAT treatment enum: `MARGIN` (VAT-margin scheme, most used stock), `QUALIFYING` (VAT-qualifying,
  VAT reclaimable/chargeable), `COMMERCIAL`, `NONE`. For MVP maths, VAT on **buyer fees** is modelled
  explicitly; VAT on the vehicle sale margin is out of scope for the bid calculation (documented in
  CALCULATION_ENGINE.md) because margin-scheme VAT depends on realised sale price, not the bid.
- Buyer-fee input can be VAT-inclusive or VAT-exclusive; the engine normalises to ex-VAT + explicit VAT line.

## Bids & reserves
- **Safe max bid**: conservative sale price, high-end (max) cost estimates, full risk reserve, full target profit.
- **Absolute max bid**: expected sale price, most-likely (estimated) costs, a **mandatory minimum risk
  reserve** (default £150 or the dealership's `mandatory_min_risk_reserve`), full target profit.
- **Break-even bid**: expected sale price and expected costs, zero target profit, zero risk reserve.
- Fees that depend on hammer price are solved with a **bisection solver** (monotonic in hammer), which
  handles tiered/percentage/min/max fees generally without algebra per fee shape. Tolerance £0.01.

## Scenarios
- **Pessimistic** = conservative sale price − expected discount, with max-end costs.
- **Expected** = expected sale price − expected discount, with estimated costs.
- **Optimistic** = optimistic sale price − (expected discount × 0.5), with min-end costs.
- These are deterministic bands from user-entered ranges, not random or ML output.

## Risk scoring
- Weighted 0–100 score across 12 factors with configurable dealership weights.
- Bands: 0–24 Low, 25–49 Medium, 50–69 High, 70–100 Critical.
- Critical hard flags (stolen / outstanding finance) **block BUY/STRONG_BUY** but do not auto-PASS a
  Cat N/S vehicle — category handling is dealership policy (`allow_category_n`, `allow_category_s`).

## Recommendation thresholds (dealership-configurable defaults)
- `target_profit` default £1,200; `min_roi` default 0.15 (15% on cash invested).
- STRONG_BUY needs expected profit ≥ 125% of target, positive pessimistic profit, ROI ≥ threshold,
  risk ≤ Medium, no critical flag.
- `max_acceptable_pessimistic_loss` default −£500 (breach ⇒ HIGH_RISK).

## Data provenance
- Every externally-sourced field records a `data_source` = `MANUAL | MOCK_ADAPTER | CSV_IMPORT`.
  The UI labels mock/manual data. No field is ever labelled as coming from a real named provider.

## Auth
- Access token TTL 15 min; refresh token TTL 7 days, **rotated** on each refresh; old refresh token is
  revoked (stored server-side, hashed). Logout revokes the active refresh token.
- Refresh token delivered as an **HTTP-only, SameSite=Lax** cookie; access token kept in memory client-side.
- Password hashing: **Argon2id** (argon2-cffi), bcrypt fallback documented.
- Auth endpoints are rate-limited (default 10 requests / minute / IP, in-memory limiter for MVP;
  Redis-backed noted for production).

## Scope trade-offs for the MVP
- Alembic ships an initial migration; the app can also `create_all` for first-run/dev convenience.
- Rate limiting and audit use in-process implementations (documented Redis/queue upgrade path).
- PDF export is generated as a print-optimised HTML appraisal sheet (browser "Save as PDF"); a server-side
  PDF renderer is a documented next step.
- Frontend implements every core screen against the live API; some secondary admin CRUD (e.g. editing an
  individual fee band inline) is provided via the API + forms but kept visually minimal.
