# Data Model

16 tables (SQLAlchemy 2 declarative; Alembic-migrated). Money is `Numeric(12,2)`; ratios `Numeric(6,4)`.
Every business row carries a `dealership_id` for multi-tenant isolation.

## Organisation
- **dealerships** — profile + calculation defaults (`default_target_profit`, `default_risk_reserve`,
  `mandatory_min_risk_reserve`, `default_min_roi`, `vat_rate`, `max_acceptable_pessimistic_loss`,
  `allow_category_n/s`, `risk_weights` JSON).
- **users** — `dealership_id`, name, email (unique), `password_hash` (Argon2), `role`, `active`.
- **refresh_tokens** — hashed refresh token, `expires_at`, `revoked` (for rotation & revocation).

## Catalogue
- **auction_houses** — `dealership_id`, name, `fee_calc_type`, default transport, active.
- **auction_fee_bands** — `fixed_fee`, `percentage`, `minimum_fee`, `maximum_fee`, `lower_bound`,
  `upper_bound`, `vat_applicable`, `stated_inclusive`, effective dates. Configurable, never hard-coded.
- **vehicles** — identity + spec (reg, VIN, make/model/derivative, dates, mileage, fuel, transmission,
  engine, body, colour, keepers, keys, euro/ULEZ, `category_marker`, `imported`, `data_source`).
- **vehicle_histories** — 1:1 with vehicle; MOT counts, defect counts, finance/stolen/write-off/mileage
  markers, plate/keeper changes, service-history status, provider, `data_retrieved_at`.
- **auction_listings** — links vehicle ↔ auction house; lot, datetime, guide, CAP clean/average/below,
  estimated retail, starting bid, reserve, condition grade, runner status, VAT status, URL, status.

## Appraisal
- **appraisals** — valuation inputs, policy inputs, and **cached outputs** (recommendation, confidence,
  safe/absolute/break-even bids, expected/pessimistic/optimistic profit, ROI, risk level) plus the full
  `result_snapshot` JSON. The engine remains the source of truth; these columns are a denormalised cache
  for fast listing/filtering.
- **cost_items** — flexible per-appraisal costs (name, category, estimated/min/max, VAT, certainty).
- **risk_assessments** — 1:1 scores JSON, weighted total, level, explanations, warning/critical flags,
  suggested reserve.
- **market_comparables** — source, asking price, mileage, year, trim, distance, seller type, days listed.

## Trading (actuals)
- **purchases** — 1:1 with appraisal; actual hammer, fees, transport, date, funding, stock number,
  prep status, buyer.
- **preparation_costs** — actual (not estimated) prep spend per purchase.
- **sales** — advertised/final price, discounts, warranty/advertising/finance, part-ex, other
  income/costs, computed `gross_profit`, `net_contribution`, `days_in_stock`.

## Audit
- **audit_logs** — append-only: actor, timestamp, action, entity, entity_id, old/new value JSON,
  request_id.

## Key relationships

```
dealership 1─* users, auction_houses, vehicles, listings, appraisals, purchases, sales, audit_logs
vehicle    1─1 vehicle_history      1─* listings, appraisals
auction_house 1─* fee_bands, listings
appraisal  1─* cost_items, comparables   1─1 risk_assessment, purchase
purchase   1─* preparation_costs    1─1 sale
```
