"""Daily prospect job.

Runs the scan-and-shortlist over every dealership's cars whose auction is *today* and delivers a
prospect list. Intended to be scheduled to run each morning (see scheduling notes below); it does not
schedule itself.

Run manually:
    python -m app.jobs.daily_shortlist                 # today, all dealerships
    python -m app.jobs.daily_shortlist --date 2026-08-01
    python -m app.jobs.daily_shortlist --include STRONG_BUY,BUY,CONSIDER

Scheduling (pick one; all just invoke the command above each morning):
    - Linux/cron:            0 7 * * *  cd /app && python -m app.jobs.daily_shortlist
    - Docker + cron/systemd: docker compose exec api python -m app.jobs.daily_shortlist
    - Windows Task Scheduler: a daily 07:00 task running the same command
    - GitHub Actions:        a scheduled workflow (cron) calling the command

Delivery is pluggable. The default writes a JSON file under ``PROSPECTS_DIR`` (or the scratch dir) and
logs a summary. Wire an email/Slack/webhook delivery by implementing ``deliver`` — the data is already
structured for it. No third-party auction site is logged into or scraped; prospects are built from
listings already in the database (manual entry, CSV import, or a licensed feed).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import date, datetime, timezone

from sqlalchemy import select

from ..db.session import SessionLocal
from ..models.organisation import Dealership
from ..services import shortlist as shortlist_service


def deliver(dealership: Dealership, report: dict) -> str:
    """Default delivery: persist a JSON report and log a summary. Replace to email/webhook."""
    out_dir = os.environ.get("PROSPECTS_DIR", ".")
    os.makedirs(out_dir, exist_ok=True)
    stamp = report.get("due_on") or datetime.now(timezone.utc).date().isoformat()
    path = os.path.join(out_dir, f"prospects_{dealership.id}_{stamp}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    return path


async def run(on: date, include: set[str]) -> list[dict]:
    reports: list[dict] = []
    async with SessionLocal() as session:
        dealerships = (await session.execute(select(Dealership))).scalars().all()
        for dealership in dealerships:
            result = await shortlist_service.scan(
                session, dealership.id, accepted=include, due_on=on, limit=50,
            )
            result["dealership_id"] = dealership.id
            result["dealership_name"] = dealership.name
            path = deliver(dealership, result)
            print(
                f"[{dealership.name}] {on.isoformat()}: scanned {result['scanned']} due car(s), "
                f"{result['shortlisted']} prospect(s) -> {path}"
            )
            for c in result["candidates"]:
                print(
                    f"    • {c['make']} {c['model']} (lot {c['lot_number']}) "
                    f"[{c['decision']}] safe max {c['safe_max_bid']}, "
                    f"expected profit {c['expected_profit']}"
                )
            reports.append(result)
    return reports


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily auction prospect shortlist")
    parser.add_argument("--date", help="ISO date (default: today, UTC)")
    parser.add_argument("--include", default="STRONG_BUY,BUY",
                        help="Comma-separated decisions to shortlist")
    args = parser.parse_args()
    on = date.fromisoformat(args.date) if args.date else datetime.now(timezone.utc).date()
    include = {d.strip().upper() for d in args.include.split(",") if d.strip()}
    asyncio.run(run(on, include))


if __name__ == "__main__":
    main()
