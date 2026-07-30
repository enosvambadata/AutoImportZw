"use client";

import { Upload } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { DataSourceBadge } from "@/components/domain";
import { Badge, Button, Card, CardBody, EmptyState, Field, Input, Spinner } from "@/components/ui";
import { QuickAddLot } from "@/components/quick-add-lot";
import { VehicleMedia } from "@/components/vehicle-gallery";
import { useAuth } from "@/features/auth/auth-context";
import { api } from "@/lib/api";
import { formatDate, formatGBP, formatNumber } from "@/lib/format";
import type { AuctionHouse, Listing, Page } from "@/types";

export default function ListingsPage() {
  const { can } = useAuth();
  const [data, setData] = useState<Page<Listing> | null>(null);
  const [houses, setHouses] = useState<AuctionHouse[]>([]);
  const [q, setQ] = useState("");
  const [make, setMake] = useState("");
  const [houseId, setHouseId] = useState("");
  const [page, setPage] = useState(1);
  const [reload, setReload] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<AuctionHouse[]>("/auction-houses").then(setHouses).catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    api
      .get<Page<Listing>>("/listings", {
        make: make || undefined,
        auction_house_id: houseId || undefined,
        page,
        page_size: 10,
      })
      .then(setData)
      .finally(() => setLoading(false));
  }, [make, houseId, page, reload]);

  const filtered =
    data?.items.filter((l) =>
      q
        ? `${l.vehicle?.make} ${l.vehicle?.model} ${l.vehicle?.registration}`
            .toLowerCase()
            .includes(q.toLowerCase())
        : true,
    ) ?? [];

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-gradient-to-br from-brand-700 via-brand-600 to-indigo-500 p-6 text-white shadow-sm">
        <div>
          <h1 className="text-2xl font-bold">Auction listings</h1>
          <p className="text-sm text-white/80">Browse the catalogue with photos and 360° views, then start an appraisal.</p>
        </div>
        {can("write") && (
          <div className="flex flex-wrap gap-2">
            <QuickAddLot onAdded={() => setReload((x) => x + 1)} />
            <Link href="/listings/import">
              <Button variant="secondary" className="bg-white/15 text-white hover:bg-white/25 border-white/20">
                <Upload size={16} /> Import CSV
              </Button>
            </Link>
          </div>
        )}
      </div>

      <Card>
        <CardBody className="grid gap-3 md:grid-cols-3">
          <Field label="Search">
            <Input placeholder="Make, model or registration" value={q} onChange={(e) => setQ(e.target.value)} />
          </Field>
          <Field label="Make">
            <Input placeholder="e.g. Ford" value={make} onChange={(e) => { setPage(1); setMake(e.target.value); }} />
          </Field>
          <Field label="Auction house">
            <select
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              value={houseId}
              onChange={(e) => { setPage(1); setHouseId(e.target.value); }}
            >
              <option value="">All</option>
              {houses.map((h) => (
                <option key={h.id} value={h.id}>{h.name}</option>
              ))}
            </select>
          </Field>
        </CardBody>
      </Card>

      {loading ? (
        <Card><CardBody><Spinner label="Loading listings…" /></CardBody></Card>
      ) : filtered.length === 0 ? (
        <Card><CardBody><EmptyState title="No listings match your filters" /></CardBody></Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((l) => {
            const seed = l.vehicle?.registration || `${l.vehicle?.make}-${l.vehicle?.model}-${l.id}`;
            const label = `${l.vehicle?.make ?? ""} ${l.vehicle?.model ?? ""}`.trim();
            return (
              <div key={l.id} className="group overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm transition-shadow hover:shadow-md">
                <VehicleMedia seed={seed} label={label} images={l.image_urls} spin={l.spin_urls} className="aspect-[16/10] w-full" />
                <div className="space-y-2 p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-semibold text-slate-900">{label}</p>
                      <p className="text-xs text-slate-500">{l.vehicle?.derivative}</p>
                    </div>
                    <p className="shrink-0 text-right">
                      <span className="block text-xs text-slate-400">Guide</span>
                      <span className="font-semibold text-slate-900">{formatGBP(l.guide_price)}</span>
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                    <span>{l.vehicle?.registration}</span>
                    <span>· {formatNumber(l.vehicle?.mileage)} mi</span>
                    <span>· Lot {l.lot_number}</span>
                    {l.vehicle?.category_marker && <Badge tone="amber">Cat {l.vehicle.category_marker}</Badge>}
                  </div>
                  <div className="flex items-center justify-between pt-1">
                    <span className="text-xs text-slate-400">{formatDate(l.auction_datetime)}</span>
                    <div className="flex items-center gap-2">
                      <DataSourceBadge source={l.data_source} />
                      {can("write") && (
                        <Link href={`/appraisals/new?listing=${l.id}`}>
                          <Button variant="secondary" className="px-3 py-1 text-xs">Appraise</Button>
                        </Link>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {data && data.total > data.page_size && (
        <div className="flex items-center justify-between text-sm text-slate-600">
          <span>{data.total} listings</span>
          <div className="flex gap-2">
            <Button variant="secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Previous</Button>
            <Button variant="secondary" disabled={page * data.page_size >= data.total} onClick={() => setPage((p) => p + 1)}>Next</Button>
          </div>
        </div>
      )}
    </div>
  );
}
