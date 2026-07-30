# User Guide

> AutoBid Intelligence is **decision support**. Every figure is an estimate; you remain responsible for
> your bids. A physical/mechanical inspection may still be needed.

## Signing in

Go to `/login`. Use a demo account (password `Password123!`):

- `admin@example.com` — administrator
- `buyer@example.com` — buyer / appraiser
- `viewer@example.com` — viewer (read-only)

## Dashboard

Shows vehicles appraised, strong buys & buys, passed vehicles, average **expected** vs **actual**
profit, average days in stock, estimated capital in stock, profit forecast, appraisal→purchase
conversion, recent appraisals and items requiring action. Estimated/forecast/actual figures are
labelled distinctly.

## Auction listings

Search and filter the catalogue (make, auction house, guide, etc.), then **Appraise** a lot to launch
the wizard pre-filled from the listing. Buyers can also **Import CSV** (template download, validated
preview, duplicate detection).

## New appraisal (7-step wizard)

1. **Vehicle** — identity/spec (registration lookup via the mock adapter is available).
2. **Auction** — house, lot, guide, current bid, condition, runner status.
3. **History** — MOT counts and markers (mileage discrepancy, finance, stolen, service history).
4. **Valuation** — expected/conservative/optimistic retail, discount, pricing confidence (a demo
   valuation can be fetched from the mock adapter).
5. **Costs** — flexible cost lines with min/estimated/max. Auction buyer fees are calculated
   automatically from the house's fee bands.
6. **Profit** — target profit, minimum ROI, risk reserve, expected days to sell.
7. **Result** — recommendation with reasons, safe/absolute/break-even bids, expected/worst/best profit,
   ROI, risk score, **bid ladder** and **sensitivity matrix**. Save to persist.

## Appraisal detail

Full vehicle summary, the calculation result, cost and risk breakdowns, and actions: **Auction mode**,
print (PDF via the browser), duplicate, mark passed, and **mark purchased** (requires explicit
confirmation).

## Auction Mode

A live-bidding screen: enter the current bid and watch **Safe maximum**, **Absolute maximum**,
**remaining room** and approximate expected profit update. A large **STOP** indicator (icon + label,
not colour alone) appears when the bid exceeds the absolute maximum; a **CAUTION** band appears above
the safe maximum.

## Stock & sales

Purchased vehicles appear here. Record **actual** preparation costs, then **complete a sale** (selling
price, warranty, advertising, finance commission). The system computes gross profit, net contribution
and days in stock, and the dashboard/analytics then compare estimated vs actual.

## Settings (admin)

Dealership calculation defaults, mandatory risk reserve, minimum ROI, VAT rate, category policy
(allow/disallow Cat N/S), auction houses & fee bands, and user management. Viewers see settings as
read-only; the API enforces this regardless of the UI.
