# tokunbo.select-style Import Concierge — Plan (Zimbabwe market)

Model we're copying: **[tokunbo.select](https://tokunbo.select/)** — a car **import sourcing/concierge
service**, NOT an inventory reseller. The buyer commits first; we source, vet, cost, buy on approval,
and import. Their pitch: *"Smart Buying. Zero Guesswork."* — they lead with **landed-cost transparency
and risk-vetting**, not flashy photos.

**Our version:** source **UK auction cars (right-hand drive)** for buyers in **Zimbabwe**, vetted with
AutoBid (MOT history + damage + write-off category), quoted as a full landed cost in **USD**, bought
on buyer approval + deposit, then exported and shipped.

This doc is the roadmap. Nothing here is built yet.

---

## 1. The model (concierge, capital-light)

Their staged process, adapted to UK → Zimbabwe:

| Stage | tokunbo.select (US→Nigeria) | Ours (UK→Zimbabwe) | Tool |
|---|---|---|---|
| 1. Source | Find US auction/dealer cars to brief | Curate UK auction lots (IAA/Copart UK) we've hand-picked; or take a buyer brief | AutoBid paste-a-listing (no scraping) |
| 2. Review | VIN history, title, mileage, damage | **MOT history + write-off category + damage scan** | AutoBid (DVSA live + Claude damage) |
| 3. Cost estimate | Landed cost in ₦ and $ | **Landed cost in USD** (+ local), itemised | New landed-cost model |
| 4. Approve + deposit | Nothing bought without approval | Buyer approves the quote, pays a deposit | Storefront enquiry/reserve |
| 5. Facilitate | Buy, export, ocean freight, customs, repairs, deliver | Buy at auction (up to AutoBid safe-max), export, ship to port, inland to buyer | AutoBid bid + manual ops |

**Key difference from a normal dealer site:** we don't hold stock. The public catalogue is a **curated
shortlist we publish manually**, each already appraised, with a landed-cost quote. Capital comes from
the buyer's deposit, not us buying on spec.

**No scraping:** candidate cars are ones we've personally chosen and pasted in — never an automated feed
off SYNETIQ/Copart/Auto Trader. Same boundary AutoBid already holds.

---

## 2. How it relates to AutoBid

- **AutoBid = private engine.** Appraise a candidate, compute safe-max bid, produce the landed-cost
  quote, and (after approval) guide bidding. Already built: MOT (DVSA live), damage scan, paste-listing,
  bid maths.
- **tokunbo-style storefront = public front.** Curated candidate cars with landed cost, the MOT/reg
  checker tool, a shipping estimator, the process + trust content, and enquiry/reserve capture.

Shared FastAPI + Postgres backend; storefront is a separate `apps/storefront` Next.js app reading a
**public read-only API** that only exposes what we deliberately publish.

---

## 3. Public site structure

```
/                     Home — "Import a vetted UK car to Zimbabwe. Zero guesswork." + trust stats
/cars                 Curated candidates — grid, filter by budget (USD), body, make; each shows landed cost
/car/[slug]           Candidate page (see §5): appraisal + MOT + landed cost + optional video + Reserve
/check                MOT/reg checker — enter a UK reg, show its MOT history (our version of their VIN checker)
/shipping             Shipping & duties estimator (UK → Zimbabwe)
/how-it-works         The 5 stages; what a deposit does; timelines
/success              Delivered imports with full cost breakdowns (trust)
/start                Buyer brief form ("tell us what you want, your budget") + WhatsApp
/about, /faq
```

Admin (inside AutoBid): **"Publish as candidate"** on an appraised car → creates/edits its public listing.

---

## 4. Data model additions

- **`Candidate` / `SaleListing`** — a car we've appraised and published as sourcing candidate:
  `vehicle_id`, `status` (DRAFT/PUBLISHED/RESERVED/SOURCING/SHIPPED/DELIVERED/WITHDRAWN), `slug`,
  `asking_bid_ceiling` (our safe-max, internal), `headline`, `blurb`, `video_url` (optional),
  landed-cost inputs, `published_at`.
- **`ImportQuote`** — the landed-cost breakdown shown to the buyer (car + fees + freight + duty + repairs).
- **`Enquiry` / `Reservation`** — buyer, car (or brief), `deposit_amount`, `deposit_status`, WhatsApp/email.
- **`BuyerBrief`** — for the "tell us what you want" flow: make/model/budget/notes, unlinked to a car.

Public API serialises only safe fields — never our bid ceiling, margin, or internal costs.

---

## 5. The candidate car page

Leads with **vetting + cost**, like the reference (photos secondary):

1. **Landed cost, itemised** — "$18,400 delivered to Harare" with the breakdown (car + auction fees +
   UK transport + ocean freight + Zim duty/VAT + inland + est. repairs). Always "estimate."
2. **MOT record** — expiry + pass/fail history + test table (built). The overseas-buyer trust signal.
3. **Condition** — damage-scan summary, write-off category, honest notes. No guarantees.
4. **Short video (optional)** — your walkaround + why you rate it. Adds personal trust; not required.
5. **Photos / 360°** — reuse existing gallery.
6. **Reserve with deposit** / **Enquire on WhatsApp**.

---

## 6. Landed-cost model (UK → Zimbabwe, USD)

```
landed_usd = winning_bid + auction_fees + uk_transport + ocean_freight(port)
           + zim_duty(car_value, engine, age) + inland_from_port + est_repairs + our_service_fee
```

- **Currency: USD.** Zimbabwe transacts heavily in USD, so quote in USD (optionally show local).
- **Ports:** Durban (RSA) or Beira (Mozambique) → inland to Harare/Bulawayo (Zimbabwe is landlocked).
- **Duty:** Zimbabwe import duty varies by type/engine/age — start with **you entering the duty
  estimate per car**; later a rule table. Always label "final duty set by ZIMRA."
- **Our service fee** = the concierge margin, stated or built into the quote.
- MVP: you enter freight/duty/repairs per car; the page renders the breakdown.

---

## 7. Trust & proof (this model lives on it)

- **Stats block** like theirs: "N imports delivered · avg X days · $ saved vs local."
- **Success stories** with full cost breakdowns.
- **Vetting front-and-centre** — MOT + damage review required before any bidding; show it.
- **Staged deposits + written terms** — nothing bought without approval; clear refund terms.
- **WhatsApp** contact (dominant in Zimbabwe).
- Honesty/no-guarantee disclaimers carry over from AutoBid. Publish only our own picks (no scraping).

---

## 8. Phased roadmap

**Phase 0 — this doc.** Confirm the concierge model and cut scope.

**Phase 1 — MVP concierge front:**
- `Candidate`/`SaleListing` + `Enquiry` + `BuyerBrief` models & migration; "Publish as candidate" in AutoBid.
- Public read-only API (`/api/public/cars`, `/car/{slug}`, MOT-check passthrough).
- `apps/storefront`: Home (+ trust stats), `/cars`, `/car/[slug]` (landed cost + MOT + condition + optional
  video), `/check` (reg→MOT), `/start` brief form + WhatsApp. Manual landed cost per car.
- Deploy to `tokunbo.select` (or your final domain).

**Phase 2 — Reserve, cost, proof:**
- Reserve-with-deposit (status + deposit tracking, manual confirm).
- Shipping/duty estimator with saved rates (ports, Zim duty rules).
- `/how-it-works`, `/success` stories, `/faq`, buyer terms.

**Phase 3 — Scale:**
- Online deposit payment (Paystack/Stripe), buyer accounts, saved cars.
- Auto landed-cost from rate/duty tables; more destinations.
- SEO, WhatsApp catalogue, conversion analytics.

---

## 9. Open decisions (your call)

1. **Domain** — `tokunbo.select` is a live *competitor* (US→Nigeria). You need your **own** domain
   (e.g. a Zimbabwe-focused name / `.co.zw`). Confirm what to register.
2. **Sourcing region** — UK only (RHD, fits AutoBid), or also Japan (the other big RHD source for Zimbabwe)?
3. **Destinations** — Zimbabwe only first, or Zambia/Malawi/DRC too?
4. **Freight/clearing** — you end-to-end, or partner with a freight/clearing agent the buyer pays?
5. **Deposit & payment** — WhatsApp + bank transfer to start (recommended), or online payment day one?
6. **Video** — required per car, or optional "nice-to-have" on top of the cost/MOT backbone?
7. **Service fee** — shown as a line item, or baked into the landed price?
