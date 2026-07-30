# API Integrations

All external data sources sit behind **interfaces** (`app/integrations/base.py`, Python `Protocol`s)
so mock adapters can be swapped for licensed services without touching business logic.

## Providers

| Interface | MVP adapter | Production equivalent (licensed) |
|-----------|-------------|----------------------------------|
| `VehicleIdentityProvider` | `MockVehicleIdentityProvider` | DVLA Vehicle Enquiry Service |
| `MotHistoryProvider` | `MockMotHistoryProvider` | DVSA MOT History API |
| `VehicleHistoryProvider` | `MockVehicleHistoryProvider` | Licensed HPI/provenance provider |
| `ValuationProvider` | `MockValuationProvider` | CAP HPI |
| `MarketComparablesProvider` | `MockMarketComparablesProvider` | Auto Trader retailer services |
| `AuctionListingProvider` | `MockAuctionListingProvider` | Auction-house data feed |

## Mock behaviour

Mock adapters (`app/integrations/mock.py`) are **deterministic** — responses are seeded from the
registration/vehicle string, so the same input always yields the same output (repeatable demos and
tests). Every payload carries `data_source = "MOCK_ADAPTER"`, and the UI labels it clearly
(`Demo data (mock)`). **No mock data is ever presented as coming from a real named provider.**

The lookup endpoints (`/api/v1/lookups/registration`, `/api/v1/lookups/valuation`) return a
`provenance` field and a disclaimer to make provenance unambiguous.

## Enabling a licensed provider

1. Implement the provider from `app/integrations/placeholders.py` (which currently raises
   `NotImplementedError` with the required-credentials message).
2. Substitute it in `registry.get_providers()` behind an environment flag.
3. Store credentials as secrets (never in source).

## Boundaries

The platform does **not** scrape websites or bypass access controls, and does not imply automatic
access to CAP HPI, Auto Trader or live auction feeds without the appropriate agreements and
credentials. These are future, licensed capabilities.

## Auctioneer connector & daily shortlist

**Scanning a named auctioneer's catalogue.** The platform connects to an auction house's catalogue via
its **official API/data feed under a commercial agreement** (`AuctioneerConnector` in
`app/integrations/placeholders.py`), authenticated with API credentials held as secrets
(`AUCTIONEER_API_URL`, `AUCTIONEER_API_KEY`). It does **not** log into the auction website with a
dealer's personal username/password and does **not** scrape the site — that would typically breach the
auctioneer's terms of use and access controls. Until an agreement + credentials are configured the
connector raises `NotImplementedError`; the compliant way to bring in real catalogue data today is
**CSV import**.

**Daily prospect shortlist.** `app/services/shortlist.py` runs every catalogue listing through the
calculation + risk + recommendation engines and returns a ranked shortlist of cars worth bidding on.
Listings without a full appraisal are scored with a *conservative automated estimate* (labelled
`AUTOMATED_ESTIMATE`) so a raw catalogue can still be triaged.

- **API:** `GET /api/v1/shortlist?due_today=true&include=STRONG_BUY,BUY` (also `due_on=<date>`,
  `auction_house_id`, `limit`).
- **UI:** the *Daily shortlist* screen, with a "cars due today only" toggle.
- **Scheduled job:** `python -m app.jobs.daily_shortlist` scans every dealership's cars **due that
  day** and delivers a prospect report (default: JSON file + log summary; wire email/Slack/webhook by
  implementing `deliver`). Schedule it to run each morning — cron, Windows Task Scheduler, a systemd
  timer, or a scheduled GitHub Actions workflow (examples in the job's docstring and DEPLOYMENT.md).
  The job never scrapes; it reads listings already in the database.

## Data connectors — Copart, SYNETIQ, Auto Trader (making it data-based)

The platform ingests real auction data through **connectors** behind a shared interface
(`app/integrations/connectors/`). A connector authenticates against a provider's **official API**
(never scraping) and returns a `NormalizedListing` / `NormalizedValuation`; the **ingestion service**
(`app/services/ingestion.py`) upserts those into the database (idempotent — re-syncing updates, never
duplicates). Everything downstream — shortlist, appraisals, analytics — then runs on the persisted
rows, so the whole system is data-based regardless of source.

| Connector | Kind | What it needs | Env vars |
|-----------|------|---------------|----------|
| `copart` | Catalogue | Copart business account with API/data-feed approval | `COPART_API_URL`, `COPART_API_KEY` |
| `synetiq` | Catalogue | SYNETIQ trade/buyer account with data-feed access | `SYNETIQ_API_URL`, `SYNETIQ_API_KEY` |
| `autotrader` | Valuation | Auto Trader **Connect** account with API key + secret | `AUTOTRADER_API_URL`, `AUTOTRADER_API_KEY`, `AUTOTRADER_API_SECRET` |
| `demo` | Catalogue | — (always available) | — |

**Connecting a real provider:** (1) obtain official API access under a commercial agreement,
(2) set the env vars, (3) implement the connector's `_map_lot()` / `_map_valuation()` to translate
that provider's response into the normalised shape (the request skeleton and the exact place to add
the mapping are marked in `providers.py`). Until mapped, the connector reports *configured* but its
`fetch`/`valuation` raises a clear `NotImplementedError` — it never invents data, and it never
scrapes the website or bypasses access controls.

**API:**
- `GET /api/v1/connectors` — status of every connector (configured or not).
- `POST /api/v1/connectors/{name}/sync` (admin) — pull the catalogue and upsert listings. The `demo`
  connector works out of the box so the pipeline can be exercised end-to-end without credentials.
- Auto Trader, once configured, automatically powers `GET /api/v1/lookups/valuation` (the wizard's
  "Fetch valuation") with live retail pricing labelled `AUTO_TRADER`; otherwise the mock is used.

**Today, without agreements:** use the `demo` connector to see the pipeline, and **CSV import** to
bring in real catalogue data compliantly.

## Registration look-up (DVLA VES + DVSA MOT)

`GET /api/v1/lookups/registration?reg=...` returns vehicle identity + MOT + history. It powers the
Quick-add **Look up** button (type a plate → auto-fill make/model/year). Providers are selected
automatically:

| Field source | Provider | Env vars | Notes |
|--------------|----------|----------|-------|
| Identity (make, year, fuel, colour, engine) | **DVLA Vehicle Enquiry Service** (`gov.py`) | `DVLA_VES_API_KEY` | Free; `x-api-key`. VES returns make but **not model**. |
| Model + MOT history | **DVSA MOT History** (`gov.py`) | `DVSA_MOT_API_KEY`, `DVSA_MOT_CLIENT_ID`, `DVSA_MOT_CLIENT_SECRET`, `DVSA_MOT_TOKEN_URL` | Free; OAuth2 client credentials + API key. Supplies the model VES lacks. |
| Everything else / no keys | **Mock adapter** | — | Deterministic demo data, labelled `MOCK_ADAPTER`. |

The endpoint merges DVSA's model into the DVLA identity, and reports `provenance` as `DVLA_DVSA`
(official) or `MOCK_ADAPTER`. Real HTTP calls degrade to the mock on failure so look-up never breaks.
These are sanctioned government APIs — sign up on the DVLA and DVSA developer portals (search "DVLA
Vehicle Enquiry Service API" and "DVSA MOT History API"). Provenance/history markers (finance,
write-off, stolen) require a separate **licensed HPI provider** (paid) — not government.

## Photo damage analysis (Claude vision advisor)

`POST /api/v1/vision/damage` accepts uploaded vehicle photos and returns a structured assessment of
**visible** damage — panels, severity, rough GBP repair ranges, suggested cost items, recommended
physical checks and tailored advisor notes. It can optionally attach the suggested cost items to an
appraisal and recalculate it (`attach_costs=true`).

- **Provider:** Claude vision (`ClaudeDamageAnalysisProvider`, model `claude-opus-4-8`) via the
  official Anthropic SDK, using image blocks + structured output (`output_config.format`) and the
  dealership/vehicle context ("your details") so advice is tailored. Selected automatically when
  `ANTHROPIC_API_KEY` is set.
- **Mock fallback:** when no key is configured, a deterministic `MockDamageAnalysisProvider` returns a
  clearly-labelled demonstration result (`analysis_source = MOCK_ADAPTER`) so the feature works
  offline. `GET /api/v1/vision/status` reports which analyser is active; the UI badges it.
- **Boundaries:** it assesses **visible** damage from photos only — never a physical or mechanical
  inspection, and it never guarantees condition or profit. This is an interim capability until a
  dedicated vehicle-damage-detection data connector is licensed; the provider interface
  (`DamageAnalysisProvider`) lets that connector drop in later.

## CSV import

As an always-available alternative to feeds, `/api/v1/imports/` provides a downloadable template and a
validated preview (per-row errors, duplicate detection, import summary). Imported data is labelled
`CSV_IMPORT`.
