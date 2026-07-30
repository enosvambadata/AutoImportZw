"use client";

import { CheckCircle2, Octagon, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { Button, Card, CardBody, Spinner } from "@/components/ui";
import { auctionStatus } from "@/features/appraisals/auction-status";
import { api } from "@/lib/api";
import { formatGBP, toNumber } from "@/lib/format";
import type { Appraisal, Vehicle } from "@/types";

export default function AuctionModePage() {
  const { id } = useParams<{ id: string }>();
  const [appraisal, setAppraisal] = useState<Appraisal | null>(null);
  const [vehicle, setVehicle] = useState<Vehicle | null>(null);
  const [bid, setBid] = useState<number>(0);

  useEffect(() => {
    api.get<Appraisal>(`/appraisals/${id}`).then((a) => {
      setAppraisal(a);
      setBid(toNumber(a.current_bid ?? a.safe_max_bid ?? "0") || 0);
      if (a.vehicle_id) api.get<Vehicle>(`/vehicles/${a.vehicle_id}`).then(setVehicle);
    });
  }, [id]);

  const safe = toNumber(appraisal?.safe_max_bid);
  const absolute = toNumber(appraisal?.absolute_max_bid);

  const status = useMemo(() => {
    if (!appraisal) return "loading";
    return auctionStatus(bid, safe, absolute);
  }, [bid, safe, absolute, appraisal]);

  // Expected profit at the entered bid, straight from the persisted snapshot's bid ladder is
  // approximate; for precision we linearly read the reference expected profit adjusted by bid.
  const ladder = appraisal?.result_snapshot?.calculation?.bid_ladder ?? [];
  const nearest = ladder.reduce<null | (typeof ladder)[number]>((best, r) => {
    if (!best) return r;
    return Math.abs(toNumber(r.hammer) - bid) < Math.abs(toNumber(best.hammer) - bid) ? r : best;
  }, null);

  if (!appraisal) return <Spinner label="Loading auction mode…" />;

  const room = absolute - bid;

  const banner =
    status === "stop"
      ? { bg: "bg-red-600", text: "text-white", label: "STOP — DO NOT BID", icon: <Octagon size={48} /> }
      : status === "caution"
        ? { bg: "bg-amber-400", text: "text-amber-950", label: "CAUTION — ABOVE SAFE MAXIMUM", icon: <TriangleAlert size={48} /> }
        : { bg: "bg-emerald-500", text: "text-white", label: "WITHIN SAFE RANGE", icon: <CheckCircle2 size={48} /> };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between print:hidden">
        <div>
          <p className="text-sm text-slate-500">Auction mode</p>
          <h1 className="text-2xl font-bold text-slate-900">
            {vehicle?.make} {vehicle?.model} · Lot {appraisal.auction_listing_id ? "#" + appraisal.auction_listing_id : "—"}
          </h1>
        </div>
        <Link href={`/appraisals/${id}`}><Button variant="secondary">Exit</Button></Link>
      </div>

      <div className={`flex items-center justify-center gap-4 rounded-2xl ${banner.bg} ${banner.text} p-8`} role="status" aria-live="assertive">
        {banner.icon}
        <span className="text-3xl font-extrabold tracking-tight">{banner.label}</span>
      </div>

      <Card>
        <CardBody className="space-y-4">
          <label className="block text-center">
            <span className="text-sm font-medium text-slate-500">Current bid (£)</span>
            <input
              type="number"
              value={bid}
              onChange={(e) => setBid(Number(e.target.value))}
              className="mt-1 w-full rounded-lg border border-slate-300 px-4 py-4 text-center text-5xl font-bold tabular-nums focus:border-brand-500 focus:outline-none"
            />
          </label>
          <input
            type="range"
            min={0}
            max={Math.round(absolute * 1.3)}
            value={bid}
            onChange={(e) => setBid(Number(e.target.value))}
            className="w-full"
            aria-label="Adjust current bid"
          />
        </CardBody>
      </Card>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Card><CardBody><p className="text-xs uppercase text-slate-500">Safe maximum</p><p className="text-2xl font-bold text-emerald-600">{formatGBP(safe)}</p></CardBody></Card>
        <Card><CardBody><p className="text-xs uppercase text-slate-500">Absolute maximum</p><p className="text-2xl font-bold text-red-600">{formatGBP(absolute)}</p></CardBody></Card>
        <Card><CardBody><p className="text-xs uppercase text-slate-500">Remaining room</p><p className={`text-2xl font-bold ${room < 0 ? "text-red-600" : "text-slate-900"}`}>{formatGBP(room)}</p></CardBody></Card>
        <Card><CardBody><p className="text-xs uppercase text-slate-500">Expected profit (approx)</p><p className="text-2xl font-bold text-slate-900">{nearest ? formatGBP(nearest.expected_profit) : "—"}</p></CardBody></Card>
      </div>

      <p className="text-center text-sm text-slate-500">
        Exceeding the absolute maximum reduces your expected target profit. Figures are estimates — you remain responsible for the bid.
      </p>
    </div>
  );
}
