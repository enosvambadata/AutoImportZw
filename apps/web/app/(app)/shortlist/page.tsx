"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Disclaimer, RecommendationBadge, RiskBadge } from "@/components/domain";
import { Button, Card, CardBody, CardHeader, EmptyState, Spinner } from "@/components/ui";
import { VehicleMedia } from "@/components/vehicle-gallery";
import { api } from "@/lib/api";
import { formatDate, formatGBP, formatPercent } from "@/lib/format";
import type { Recommendation, RiskLevel } from "@/types";

interface Candidate {
  listing_id: number;
  make: string;
  model: string;
  derivative: string | null;
  registration: string | null;
  lot_number: string | null;
  auction_house: string | null;
  auction_datetime: string | null;
  guide_price: string | null;
  decision: Recommendation;
  risk_level: RiskLevel;
  safe_max_bid: string | null;
  absolute_max_bid: string | null;
  expected_profit: string | null;
  roi_on_cost: string | null;
  headline_reason: string;
}
interface ShortlistResponse {
  scanned: number;
  skipped_no_valuation: number;
  shortlisted: number;
  due_on: string | null;
  candidates: Candidate[];
  note: string;
}

export default function ShortlistPage() {
  const [data, setData] = useState<ShortlistResponse | null>(null);
  const [dueToday, setDueToday] = useState(false);
  const [wide, setWide] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    api
      .get<ShortlistResponse>("/shortlist", {
        due_today: dueToday || undefined,
        include: wide ? "STRONG_BUY,BUY,CONSIDER" : "STRONG_BUY,BUY",
      })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [dueToday, wide]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Daily shortlist</h1>
          <p className="text-sm text-slate-500">
            Automated first-pass prospects — every catalogue car ranked by the engine. Complete a full
            appraisal before bidding.
          </p>
        </div>
        <Button variant="secondary" onClick={load}>Rescan</Button>
      </div>

      <div className="flex flex-wrap items-center gap-4 text-sm">
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={dueToday} onChange={(e) => setDueToday(e.target.checked)} />
          Cars due today only
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={wide} onChange={(e) => setWide(e.target.checked)} />
          Include &ldquo;Consider&rdquo;
        </label>
      </div>

      <Card>
        <CardBody className="text-xs text-slate-500">
          Runs automatically each morning via the <code>daily_shortlist</code> job (see the deployment
          notes). Prospects are built from listings already in your catalogue (manual entry, CSV import,
          or a licensed auctioneer feed) — the platform never logs into or scrapes a third-party auction
          site with personal credentials.
        </CardBody>
      </Card>

      {error && <p className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      {loading ? (
        <Spinner label="Scanning catalogue…" />
      ) : !data ? null : (
        <>
          <div className="flex flex-wrap gap-2 text-sm text-slate-600">
            <span className="rounded bg-slate-100 px-2 py-1">Scanned {data.scanned}</span>
            <span className="rounded bg-emerald-100 px-2 py-1 text-emerald-800">{data.shortlisted} prospects</span>
            {data.due_on && <span className="rounded bg-blue-100 px-2 py-1 text-blue-800">Due {formatDate(data.due_on)}</span>}
            {data.skipped_no_valuation > 0 && (
              <span className="rounded bg-amber-100 px-2 py-1 text-amber-900">{data.skipped_no_valuation} skipped (no valuation)</span>
            )}
          </div>

          <Card>
            <CardHeader title="Prospects" subtitle="Ranked by recommendation, then expected profit" />
            <CardBody className="p-0">
              {data.candidates.length === 0 ? (
                <div className="p-5"><EmptyState title="No prospects match" description="Try including 'Consider', or add valuation data to more listings." /></div>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 text-left text-xs uppercase text-slate-500">
                      <th className="px-5 py-2 font-medium">Vehicle</th>
                      <th className="px-5 py-2 font-medium">Auction</th>
                      <th className="px-5 py-2 font-medium">Guide</th>
                      <th className="px-5 py-2 font-medium">Safe / Absolute</th>
                      <th className="px-5 py-2 font-medium">Est. profit</th>
                      <th className="px-5 py-2 font-medium">Risk</th>
                      <th className="px-5 py-2 font-medium"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.candidates.map((c) => (
                      <tr key={c.listing_id} className="border-b border-slate-50 hover:bg-slate-50">
                        <td className="px-5 py-3">
                          <div className="flex items-center gap-3">
                            <VehicleMedia
                              seed={c.registration || `${c.make}-${c.model}-${c.listing_id}`}
                              label={`${c.make} ${c.model}`}
                              className="h-14 w-20 shrink-0"
                            />
                            <div>
                              <div className="font-medium text-slate-900">{c.make} {c.model}</div>
                              <div className="text-xs text-slate-500">{c.derivative} · Lot {c.lot_number}</div>
                              <div className="mt-1"><RecommendationBadge value={c.decision} /></div>
                            </div>
                          </div>
                        </td>
                        <td className="px-5 py-3 text-slate-600">
                          {c.auction_house}
                          <div className="text-xs text-slate-400">{formatDate(c.auction_datetime)}</div>
                        </td>
                        <td className="px-5 py-3">{formatGBP(c.guide_price)}</td>
                        <td className="px-5 py-3 text-slate-600">{formatGBP(c.safe_max_bid)} / {formatGBP(c.absolute_max_bid)}</td>
                        <td className="px-5 py-3 font-medium">{formatGBP(c.expected_profit)}<div className="text-xs text-slate-400">ROI {formatPercent(c.roi_on_cost)}</div></td>
                        <td className="px-5 py-3"><RiskBadge value={c.risk_level} /></td>
                        <td className="px-5 py-3 text-right">
                          <Link href={`/appraisals/new?listing=${c.listing_id}`}>
                            <Button variant="secondary" className="px-3 py-1 text-xs">Appraise</Button>
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </CardBody>
          </Card>

          <p className="text-xs text-slate-500">{data.note}</p>
        </>
      )}

      <Disclaimer />
    </div>
  );
}
