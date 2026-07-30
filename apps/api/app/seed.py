"""Seed realistic UK demo data.

Usage:
    python -m app.seed --reset      # drop all rows and reseed
    python -m app.seed --if-empty   # seed only if the database has no dealership yet

All registrations are fictional test values. Demo users share the password below.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete, select

from .core.security import hash_password
from .db.base import Base
from .db.session import SessionLocal, engine
from .models.appraisal import Appraisal, CostItem, MarketComparable
from .models.audit import AuditLog
from .models.catalogue import AuctionFeeBand, AuctionHouse, AuctionListing, Vehicle, VehicleHistory
from .models.organisation import Dealership, RefreshToken, User
from .models.storefront import BuyerBrief, Enquiry, SaleListing
from .models.trading import PreparationCost, Purchase, Sale
from .services.appraisal_service import compute_and_store

DEMO_PASSWORD = "Password123!"

# Intended demo outcome per vehicle (index-aligned with VEHICLES). The seed first computes the
# bids, then sets current_bid relative to them so the recommendation lands as intended.
POSTURES = [
    "strong",    # 0 Ford Focus      — low-risk, healthy margin
    "highrisk",  # 1 BMW 3 Series    — wide repair range breaches pessimistic floor
    "buy",       # 2 VW Golf (Cat N) — allowed but flagged
    "consider",  # 3 Vauxhall Corsa  — mileage discrepancy, thin margin
    "passloss",  # 4 Nissan Qashqai  — non-runner, expected loss
    "passguide", # 5 Audi A4         — guide already above absolute maximum
    "consider",  # 6 Toyota RAV4     — strong profit but low ROI / slow sale
    "buy",       # 7 Kia Sportage    — fee crosses a tier boundary
    "strong",    # 8 Ford Fiesta     — clean supermini
    "buy",       # 9 VW Polo         — clean stock
    "consider",  # 10 BMW 1 Series   — no service history, one key
    "buy",       # 11 Audi Q3        — premium crossover
]


def D(x) -> Decimal:
    return Decimal(str(x))


def _posture_bid(posture: str, safe: Decimal, absolute: Decimal, break_even: Decimal) -> Decimal:
    factors = {
        "strong": safe * D("0.88"),
        "buy": absolute * D("0.985"),
        "consider": absolute * D("0.97"),
        "highrisk": absolute * D("0.95"),
        "passguide": absolute * D("1.18"),
        "passloss": break_even * D("1.12"),
    }
    return Decimal(round(factors.get(posture, safe)))


async def _reset(session) -> None:
    for model in (AuditLog, Sale, PreparationCost, Purchase, MarketComparable, CostItem,
                  Appraisal, AuctionListing, AuctionFeeBand, AuctionHouse, VehicleHistory,
                  Vehicle, RefreshToken, User, Dealership):
        await session.execute(delete(model))
    await session.commit()


# (make, model, derivative, year, mileage, fuel, trans, reg, keys, keepers, category, notes)
VEHICLES = [
    dict(make="Ford", model="Focus", derivative="Titanium 1.0 EcoBoost", year=2019, mileage=41200,
         fuel="Petrol", trans="Manual", reg="AB19FGH", keys=2, keepers=2, cat=None,
         cons=8300, exp=8900, opt=9400, guide=6200, current=6200, days=28, conf="HIGH",
         costs=[("Preparation service", "SERVICE", 220, 180, 320),
                ("Valet & detailing", "VALETING", 120, 100, 160),
                ("MOT", "MOT", 55, 40, 120)],
         profile="low-risk mainstream, healthy margin"),
    dict(make="BMW", model="3 Series", derivative="320d M Sport", year=2017, mileage=78400,
         fuel="Diesel", trans="Automatic", reg="BD17KLM", keys=2, keepers=3, cat=None,
         cons=11200, exp=12200, opt=13100, guide=8700, current=8700, days=40, conf="MEDIUM",
         costs=[("Timing chain (uncertain)", "MECHANICAL", 900, 250, 1900),
                ("Bodywork", "BODYWORK", 400, 250, 700),
                ("Transport", "TRANSPORT", 180, 150, 220),
                ("Service", "SERVICE", 320, 260, 420)],
         profile="hidden-profit risk from estimated repairs"),
    dict(make="Volkswagen", model="Golf", derivative="GT TSI", year=2018, mileage=52300,
         fuel="Petrol", trans="Manual", reg="CE18NOP", keys=2, keepers=2, cat="N",
         cons=9200, exp=10100, opt=10800, guide=6900, current=6900, days=45, conf="MEDIUM",
         costs=[("Panel respray (Cat N repair check)", "BODYWORK", 650, 400, 1100),
                ("Service", "SERVICE", 260, 220, 340),
                ("Transport", "TRANSPORT", 160, 140, 200)],
         profile="Category N vehicle"),
    dict(make="Vauxhall", model="Corsa", derivative="SRi 1.4", year=2016, mileage=61000,
         fuel="Petrol", trans="Manual", reg="DF16QRS", keys=1, keepers=4, cat=None,
         cons=4200, exp=4700, opt=5000, guide=3200, current=3200, days=35, conf="LOW",
         costs=[("Investigate mileage/service", "MECHANICAL", 300, 150, 800),
                ("Valet", "VALETING", 90, 70, 120),
                ("Second key", "KEYS", 180, 120, 240)],
         mileage_discrepancy=True, service="NONE",
         profile="mileage discrepancy"),
    dict(make="Nissan", model="Qashqai", derivative="Acenta DCi", year=2015, mileage=94500,
         fuel="Diesel", trans="Manual", reg="EG15TUV", keys=2, keepers=5, cat=None,
         cons=5100, exp=5600, opt=6000, guide=3900, current=3900, days=50, conf="MEDIUM",
         non_runner=True,
         costs=[("Non-runner diagnosis + repair", "MECHANICAL", 1400, 600, 2600),
                ("Transport (recovery)", "TRANSPORT", 260, 200, 340),
                ("Service", "SERVICE", 300, 240, 400)],
         profile="non-runner"),
    dict(make="Audi", model="A4", derivative="S line 2.0 TDI", year=2018, mileage=58200,
         fuel="Diesel", trans="Automatic", reg="FH18WXY", keys=2, keepers=2, cat=None,
         cons=12800, exp=13600, opt=14200, guide=13900, current=13900, days=42, conf="MEDIUM",
         costs=[("Service", "SERVICE", 340, 280, 440),
                ("Transport", "TRANSPORT", 190, 160, 240),
                ("Alloy refurb", "BODYWORK", 240, 180, 360)],
         profile="guide already above absolute maximum"),
    dict(make="Toyota", model="RAV4", derivative="Excel Hybrid", year=2019, mileage=46800,
         fuel="Hybrid", trans="Automatic", reg="GJ19ZAB", keys=2, keepers=1, cat=None,
         cons=17800, exp=19200, opt=20500, guide=15200, current=15200, days=88, conf="HIGH",
         costs=[("Service", "SERVICE", 300, 260, 380),
                ("Detailing", "DETAILING", 180, 150, 240),
                ("Transport", "TRANSPORT", 200, 170, 250)],
         profile="strong profit but slow expected sale"),
    dict(make="Kia", model="Sportage", derivative="2 CRDi", year=2017, mileage=64300,
         fuel="Diesel", trans="Manual", reg="HK17CDE", keys=2, keepers=3, cat=None,
         cons=8600, exp=9400, opt=10000, guide=9950, current=9950, days=38, conf="MEDIUM",
         costs=[("Service", "SERVICE", 280, 240, 360),
                ("Tyres x2", "TYRES", 220, 180, 300),
                ("Transport", "TRANSPORT", 170, 150, 210)],
         profile="buyer fees cross a tier boundary"),
    dict(make="Ford", model="Fiesta", derivative="Zetec 1.0", year=2018, mileage=38900,
         fuel="Petrol", trans="Manual", reg="JL18FGH", keys=2, keepers=2, cat=None,
         cons=6400, exp=6900, opt=7300, guide=5100, current=5100, days=25, conf="HIGH",
         costs=[("Service", "SERVICE", 200, 170, 260), ("Valet", "VALETING", 90, 70, 120)],
         profile="low-risk supermini"),
    dict(make="Volkswagen", model="Polo", derivative="SE 1.0", year=2019, mileage=33100,
         fuel="Petrol", trans="Manual", reg="KM19IJK", keys=2, keepers=1, cat=None,
         cons=7200, exp=7800, opt=8200, guide=5800, current=5800, days=30, conf="HIGH",
         costs=[("Service", "SERVICE", 210, 180, 270), ("MOT", "MOT", 55, 40, 90)],
         profile="clean stock"),
    dict(make="BMW", model="1 Series", derivative="118i Sport", year=2016, mileage=71200,
         fuel="Petrol", trans="Manual", reg="LN16LMN", keys=1, keepers=4, cat=None,
         cons=6800, exp=7500, opt=8000, guide=5400, current=5400, days=48, conf="LOW",
         service="NONE",
         costs=[("Service (no history)", "SERVICE", 380, 300, 520),
                ("Second key", "KEYS", 200, 140, 260),
                ("Transport", "TRANSPORT", 170, 150, 210)],
         profile="missing service history, one key"),
    dict(make="Audi", model="Q3", derivative="S line TFSI", year=2018, mileage=49500,
         fuel="Petrol", trans="Automatic", reg="PR18OPQ", keys=2, keepers=2, cat=None,
         cons=14200, exp=15300, opt=16100, guide=11800, current=11800, days=44, conf="MEDIUM",
         costs=[("Service", "SERVICE", 340, 280, 440),
                ("Detailing", "DETAILING", 200, 160, 260),
                ("Transport", "TRANSPORT", 210, 180, 260)],
         profile="premium crossover, solid margin"),
]


async def seed(reset: bool = False, if_empty: bool = False) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        if if_empty:
            existing = (await session.execute(select(Dealership))).scalars().first()
            if existing:
                print("Database already seeded; skipping (--if-empty).")
                return
        if reset:
            await _reset(session)

        dealership = Dealership(
            name="Pennine Motor Group Ltd", trading_name="Pennine Cars",
            company_number="09876543", vat_registered=True, vat_number="GB123456789",
            postcode="LS1 4DY", default_target_profit=D("1200"), default_risk_reserve=D("300"),
            mandatory_min_risk_reserve=D("150"), default_min_roi=D("0.15"),
            vat_rate=D("0.20"), max_acceptable_pessimistic_loss=D("-500"),
            allow_category_n=True, allow_category_s=False, risk_weights={},
        )
        session.add(dealership)
        await session.flush()

        pw = hash_password(DEMO_PASSWORD)
        admin = User(dealership_id=dealership.id, first_name="Alice", last_name="Adams",
                     email="admin@example.com", password_hash=pw, role="ADMIN")
        buyer = User(dealership_id=dealership.id, first_name="Ben", last_name="Booth",
                     email="buyer@example.com", password_hash=pw, role="BUYER")
        viewer = User(dealership_id=dealership.id, first_name="Vic", last_name="Vale",
                      email="viewer@example.com", password_hash=pw, role="VIEWER")
        session.add_all([admin, buyer, viewer])
        await session.flush()

        # Auction house 1: tiered percentage fee (crosses a boundary at £8,000), VAT applicable.
        house1 = AuctionHouse(dealership_id=dealership.id, name="Central Car Auctions",
                              website="https://example-auctions.test", fee_calc_type="TIERED",
                              default_transport_estimate=D("180"))
        house1.fee_bands = [
            AuctionFeeBand(percentage=D("0.08"), minimum_fee=D("180"), upper_bound=D("8000"),
                           vat_applicable=True, label="Up to £8,000"),
            AuctionFeeBand(percentage=D("0.06"), minimum_fee=D("320"), lower_bound=D("8000"),
                           vat_applicable=True, label="£8,000 and above"),
        ]
        # Auction house 2: percentage + fixed, VAT applicable.
        house2 = AuctionHouse(dealership_id=dealership.id, name="Northern Vehicle Remarketing",
                              website="https://example-remarketing.test",
                              fee_calc_type="PERCENTAGE_PLUS_FIXED",
                              default_transport_estimate=D("160"))
        house2.fee_bands = [
            AuctionFeeBand(percentage=D("0.05"), fixed_fee=D("95"), minimum_fee=D("225"),
                           maximum_fee=D("650"), vat_applicable=True, label="Flat 5% + £95"),
        ]
        session.add_all([house1, house2])
        await session.flush()

        appraisals: list[Appraisal] = []
        for i, v in enumerate(VEHICLES):
            house = house1 if i % 2 == 0 else house2
            reg_date = date(v["year"], 3, 15)
            vehicle = Vehicle(
                dealership_id=dealership.id, registration=v["reg"], make=v["make"],
                model=v["model"], derivative=v["derivative"], registration_date=reg_date,
                model_year=v["year"], mileage=v["mileage"], fuel_type=v["fuel"],
                transmission=v["trans"], colour="Grey", previous_keepers=v["keepers"],
                number_of_keys=v["keys"], euro_status="6" if v["year"] >= 2016 else "5",
                ulez_compliant=v["year"] >= 2016, category_marker=v.get("cat"),
                data_source="MOCK_ADAPTER",
            )
            vehicle.history = VehicleHistory(
                mot_expiry=date.today() + timedelta(days=120 + i * 10),
                mot_pass_count=3 + i % 4, mot_fail_count=(2 if v.get("non_runner") else i % 2),
                advisory_count=i % 5, major_defect_count=i % 2,
                dangerous_defect_count=1 if v.get("non_runner") else 0,
                repeated_failures=bool(v.get("mileage_discrepancy")),
                finance_marker=False, stolen_marker=False, write_off_marker=False,
                mileage_discrepancy=bool(v.get("mileage_discrepancy")),
                plate_changes=1 if v.get("mileage_discrepancy") else 0,
                keeper_changes=v["keepers"], service_history_status=v.get("service", "FULL"),
                last_service_date=date.today() - timedelta(days=200),
                last_service_mileage=v["mileage"] - 6000, history_provider="MOCK_ADAPTER",
                data_retrieved_at=datetime.now(timezone.utc),
            )
            session.add(vehicle)
            await session.flush()

            listing = AuctionListing(
                dealership_id=dealership.id, vehicle_id=vehicle.id,
                auction_house_id=house.id, lot_number=f"L{100 + i}",
                auction_datetime=datetime.now(timezone.utc) + timedelta(days=3 + i),
                guide_price=D(v["guide"]), cap_clean=D(v["exp"]) - D(200),
                cap_average=D(v["cons"]), cap_below=D(v["cons"]) - D(400),
                estimated_retail=D(v["exp"]), starting_bid=D(v["guide"]) - D(500),
                condition_grade=4 if v.get("non_runner") else (3 if v.get("cat") else 2),
                runner_status="NON_RUNNER" if v.get("non_runner") else "RUNNER",
                vat_status="MARGIN", listing_status="UPCOMING", data_source="MOCK_ADAPTER",
                mechanical_report="Mock inspection notes for demonstration.",
            )
            session.add(listing)
            await session.flush()

            appraisal = Appraisal(
                dealership_id=dealership.id, vehicle_id=vehicle.id,
                auction_listing_id=listing.id, appraiser_id=buyer.id, status="COMPLETE",
                expected_retail_price=D(v["exp"]), conservative_retail_price=D(v["cons"]),
                optimistic_retail_price=D(v["opt"]), expected_negotiated_discount=D(150),
                pricing_confidence=v["conf"], target_profit=D("1200"), risk_reserve=D("300"),
                desired_roi=D("0.15"), estimated_days_to_sell=v["days"],
                current_bid=D(v["current"]),
            )
            appraisal.cost_items = [
                CostItem(name=n, category=c, estimated_amount=D(e), minimum_amount=D(lo),
                         maximum_amount=D(hi), certainty="MEDIUM")
                for (n, c, e, lo, hi) in v["costs"]
            ]
            appraisal.comparables = [
                MarketComparable(source="MOCK_ADAPTER", listing_reference=f"C{i}-{k}",
                                 asking_price=D(v["exp"]) + D(k * 150 - 200),
                                 mileage=v["mileage"] + k * 1500 - 3000, year=v["year"],
                                 trim=v["derivative"], distance_miles=10 + k * 20,
                                 seller_type="Independent", days_listed=10 + k * 6,
                                 captured_on=date.today())
                for k in range(4)
            ]
            session.add(appraisal)
            await session.flush()
            await compute_and_store(session, appraisal)
            # Second pass: anchor current_bid to the computed bids for a realistic demo spread.
            appraisal.current_bid = _posture_bid(
                POSTURES[i], appraisal.safe_max_bid or D("0"),
                appraisal.absolute_max_bid or D("0"), appraisal.break_even_bid or D("0"))
            await compute_and_store(session, appraisal)
            appraisals.append(appraisal)

        await session.commit()

        # Convert three appraisals into purchases; sell two of them.
        buy_targets = [appraisals[0], appraisals[8], appraisals[6]]  # Focus, Fiesta, RAV4
        purchases = []
        for j, appr in enumerate(buy_targets):
            hammer = appr.safe_max_bid or D("5000")
            purchase = Purchase(
                dealership_id=dealership.id, appraisal_id=appr.id,
                actual_hammer_price=hammer, actual_auction_fees=D("300"),
                actual_transport_cost=D("180"),
                purchase_date=date.today() - timedelta(days=60 - j * 10),
                funding_source="Stocking loan", stock_number=f"PMG{2600 + j}",
                purchased_by_id=buyer.id, preparation_status="READY",
                notes="Purchased at auction (demo).",
            )
            purchase.preparation_costs = [
                PreparationCost(category="SERVICE", description="Full service",
                                actual_amount=D("260"), incurred_on=date.today() - timedelta(days=50),
                                supplier="In-house workshop"),
                PreparationCost(category="VALETING", description="Full valet",
                                actual_amount=D("110"), incurred_on=date.today() - timedelta(days=48),
                                supplier="ShineCo"),
            ]
            appr.status = "PURCHASED"
            session.add(purchase)
            purchases.append(purchase)
        await session.flush()

        # Two completed sales.
        for k, purchase in enumerate(purchases[:2]):
            sell_price = (purchase.appraisal.expected_retail_price or D("8000")) - D(150 + k * 100)
            sale = Sale(
                dealership_id=dealership.id, purchase_id=purchase.id,
                advertised_price=sell_price + D("300"), final_selling_price=sell_price,
                sale_date=purchase.purchase_date + timedelta(days=32 + k * 9),
                customer_discount=D("150"), warranty_cost=D("180"), advertising_cost=D("60"),
                finance_commission=D("220"), other_income=D("0"), other_costs=D("0"),
            )
            # Reuse the same profit maths as the API.
            from .api.v1.sales import _compute
            await session.refresh(purchase, attribute_names=["preparation_costs"])
            _compute(sale, purchase)
            purchase.preparation_status = "SOLD"
            session.add(sale)
        await session.commit()

    print("Seed complete.")
    print("  Dealership: Pennine Motor Group Ltd")
    print(f"  Users (password '{DEMO_PASSWORD}'):")
    print("    admin@example.com   (ADMIN)")
    print("    buyer@example.com   (BUYER)")
    print("    viewer@example.com  (VIEWER)")


async def wipe_data() -> None:
    """Clean-slate: delete all vehicle/appraisal/trading/catalogue data, keep dealerships + users."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        for model in (AuditLog, Enquiry, BuyerBrief, SaleListing, Sale, PreparationCost, Purchase,
                      MarketComparable, CostItem, Appraisal, AuctionListing, AuctionFeeBand,
                      AuctionHouse, VehicleHistory, Vehicle):
            await session.execute(delete(model))
        await session.commit()
    print("Data wiped. Kept your dealership(s) and user logins; removed all vehicles, listings, "
          "appraisals, purchases, sales, storefront listings, enquiries and audit history.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed / manage AutoBid data")
    parser.add_argument("--reset", action="store_true", help="Delete existing rows first, then seed")
    parser.add_argument("--if-empty", action="store_true", help="Only seed if empty")
    parser.add_argument("--wipe", action="store_true",
                        help="Clean slate: delete business data but keep dealerships + users")
    args = parser.parse_args()
    if args.wipe:
        asyncio.run(wipe_data())
    else:
        asyncio.run(seed(reset=args.reset, if_empty=args.if_empty))


if __name__ == "__main__":
    main()
