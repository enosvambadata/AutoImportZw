"use client";

import { Copy, Gavel, Printer, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppraisalResult } from "@/components/appraisal-result";
import { DamageScan } from "@/components/damage-scan";
import { DataSourceBadge } from "@/components/domain";
import { StorefrontPublish } from "@/components/storefront-publish";
import { Badge, Button, Card, CardBody, CardHeader, Field, Input, Spinner } from "@/components/ui";
import { useAuth } from "@/features/auth/auth-context";
import { api } from "@/lib/api";
import { formatDate, formatGBP, formatNumber } from "@/lib/format";
import type { Appraisal, Vehicle } from "@/types";

export default function AppraisalDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { can } = useAuth();
  const [appraisal, setAppraisal] = useState<Appraisal | null>(null);
  const [vehicle, setVehicle] = useState<Vehicle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showPurchase, setShowPurchase] = useState(false);
  const [hammer, setHammer] = useState("");
  const [confirmChecked, setConfirmChecked] = useState(false);
  const [busy, setBusy] = useState(false);

  async function load() {
    const a = await api.get<Appraisal>(`/appraisals/${id}`);
    setAppraisal(a);
    setHammer(a.safe_max_bid ?? "");
    if (a.vehicle_id) setVehicle(await api.get<Vehicle>(`/vehicles/${a.vehicle_id}`));
  }

  useEffect(() => {
    load().catch((e) => setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const [enriching, setEnriching] = useState(false);
  const [enrichNote, setEnrichNote] = useState<string | null>(null);

  async function markPassed() {
    await api.post(`/appraisals/${id}/pass`);
    load();
  }

  async function refreshData() {
    if (!appraisal?.vehicle_id) return;
    setEnriching(true);
    setEnrichNote(null);
    try {
      await api.post(`/vehicles/${appraisal.vehicle_id}/enrich`);
      await load();
      setEnrichNote("MOT & history refreshed — risk recalculated.");
    } catch (e) {
      setEnrichNote(e instanceof Error ? e.message : "Refresh failed");
    } finally {
      setEnriching(false);
    }
  }
  async function duplicate() {
    const clone = await api.post<{ id: number }>(`/appraisals/${id}/duplicate`);
    router.push(`/appraisals/${clone.id}`);
  }
  async function confirmPurchase() {
    setBusy(true);
    setError(null);
    try {
      await api.post("/purchases", {
        appraisal_id: Number(id),
        actual_hammer_price: hammer || "0",
        actual_auction_fees: "0",
        actual_transport_cost: "0",
        purchase_date: new Date().toISOString().slice(0, 10),
        confirm: true,
      });
      setShowPurchase(false);
      router.push("/stock");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Purchase failed");
    } finally {
      setBusy(false);
    }
  }

  if (error) return <p className="rounded bg-red-50 p-4 text-red-700">{error}</p>;
  if (!appraisal) return <Spinner label="Loading appraisal…" />;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            {vehicle?.make} {vehicle?.model} <span className="text-slate-400">#{appraisal.id}</span>
          </h1>
          <p className="text-sm text-slate-500">
            {vehicle?.registration} · {vehicle?.derivative} · Status {appraisal.status}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href={`/appraisals/${id}/auction`}>
            <Button variant="secondary"><Gavel size={16} /> Auction mode</Button>
          </Link>
          <Button variant="ghost" onClick={() => window.print()}><Printer size={16} /> Print</Button>
          {can("write") && <Button variant="ghost" onClick={duplicate}><Copy size={16} /> Duplicate</Button>}
          {can("write") && appraisal.status !== "PURCHASED" && (
            <>
              <Button variant="secondary" onClick={markPassed}>Mark passed</Button>
              <Button onClick={() => setShowPurchase(true)}>Mark purchased</Button>
            </>
          )}
        </div>
      </div>

      {/* Vehicle summary */}
      <Card>
        <CardHeader
          title="Vehicle summary"
          action={
            <div className="flex items-center gap-2">
              <DataSourceBadge source={vehicle?.data_source} />
              {can("write") && vehicle?.registration && (
                <Button variant="secondary" className="px-3 py-1 text-xs" disabled={enriching} onClick={refreshData}>
                  <RefreshCw size={14} className={enriching ? "animate-spin" : ""} /> {enriching ? "Refreshing…" : "Refresh MOT & history"}
                </Button>
              )}
            </div>
          }
        />
        <CardBody>
          {enrichNote && <p className="mb-2 text-xs text-emerald-700">{enrichNote}</p>}
          <dl className="grid grid-cols-2 gap-y-2 text-sm md:grid-cols-4">
            {[
              ["Registration", vehicle?.registration ?? "—"],
              ["Year", vehicle?.model_year ?? "—"],
              ["Mileage", formatNumber(vehicle?.mileage)],
              ["Fuel", vehicle?.fuel_type ?? "—"],
              ["Transmission", vehicle?.transmission ?? "—"],
              ["Keys", vehicle?.number_of_keys ?? "—"],
              ["Category", vehicle?.category_marker ?? "None"],
              ["Colour", vehicle?.colour ?? "—"],
            ].map(([k, v]) => (
              <div key={k as string}>
                <dt className="text-xs uppercase text-slate-400">{k}</dt>
                <dd className="font-medium text-slate-800">{v as string}</dd>
              </div>
            ))}
          </dl>
        </CardBody>
      </Card>

      {/* MOT & history */}
      <Card>
        <CardHeader
          title="MOT & history"
          subtitle="From the vehicle's DVSA MOT record — feeds the risk score"
          action={vehicle?.history && (
            <Badge tone={vehicle.history.history_provider?.toUpperCase().includes("DVSA") ? "green" : "slate"}>
              {vehicle.history.history_provider?.toUpperCase().includes("DVSA") ? "DVSA — live" : "Demo (mock)"}
            </Badge>
          )}
        />
        <CardBody className="space-y-3">
          {!vehicle?.history ? (
            <p className="text-sm text-slate-500">
              No MOT record yet.{vehicle?.registration ? " Click “Refresh MOT & history” above to pull it from DVSA." : " Add a registration to the vehicle, then refresh."}
            </p>
          ) : (
            <>
              <dl className="grid grid-cols-2 gap-y-2 text-sm md:grid-cols-4">
                {(() => {
                  const h = vehicle.history!;
                  const expired = h.mot_expiry ? new Date(h.mot_expiry) < new Date() : null;
                  return [
                    ["MOT expiry", h.mot_expiry ? `${formatDate(h.mot_expiry)}${expired === false ? " · valid" : expired ? " · EXPIRED" : ""}` : "—"],
                    ["Tests", `${h.mot_pass_count} pass / ${h.mot_fail_count} fail`],
                    ["Advisories", String(h.advisory_count ?? 0)],
                    ["Dangerous defects", String(h.dangerous_defect_count ?? 0)],
                    ["Mileage", h.mileage_discrepancy ? "⚠ discrepancy" : "consistent"],
                    ["Service history", h.service_history_status ?? "—"],
                    ["Source", h.history_provider ?? "—"],
                    ["Retrieved", h.data_retrieved_at ? formatDate(h.data_retrieved_at) : "—"],
                  ].map(([k, v]) => (
                    <div key={k}>
                      <dt className="text-xs uppercase text-slate-400">{k}</dt>
                      <dd className={`font-medium ${String(v).includes("EXPIRED") || String(v).includes("⚠") ? "text-red-600" : "text-slate-800"}`}>{v}</dd>
                    </div>
                  ));
                })()}
              </dl>

              {vehicle.history.mot_tests?.length > 0 && (
                <div className="overflow-x-auto border-t border-slate-100 pt-2">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-100 text-left text-xs uppercase text-slate-500">
                        <th className="py-1 pr-3 font-medium">Date</th>
                        <th className="py-1 pr-3 font-medium">Result</th>
                        <th className="py-1 pr-3 font-medium">Odometer</th>
                        <th className="py-1 pr-3 font-medium">Expiry</th>
                        <th className="py-1 pr-3 font-medium">Adv / Dang</th>
                      </tr>
                    </thead>
                    <tbody>
                      {vehicle.history.mot_tests.map((t, i) => (
                        <tr key={i} className="border-b border-slate-50">
                          <td className="py-1.5 pr-3">{t.date ? formatDate(t.date) : "—"}</td>
                          <td className="py-1.5 pr-3">
                            <Badge tone={t.result === "PASSED" ? "green" : t.result === "FAILED" ? "red" : "slate"}>{t.result ?? "—"}</Badge>
                          </td>
                          <td className="py-1.5 pr-3">{t.odometer != null ? `${formatNumber(t.odometer)} ${t.unit ?? ""}`.trim() : "—"}</td>
                          <td className="py-1.5 pr-3">{t.expiry ? formatDate(t.expiry) : "—"}</td>
                          <td className="py-1.5 pr-3">{t.advisories} / <span className={t.dangerous ? "font-semibold text-red-600" : ""}>{t.dangerous}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </CardBody>
      </Card>

      <DamageScan appraisalId={appraisal.id} onAttached={() => load()} />

      {vehicle && (
        <StorefrontPublish
          vehicleId={vehicle.id}
          appraisalId={appraisal.id}
          suggestedHeadline={`${vehicle.model_year ?? ""} ${vehicle.make} ${vehicle.model}`.trim()}
        />
      )}

      <AppraisalResult result={appraisal.result_snapshot} />

      {/* Cost breakdown */}
      <Card>
        <CardHeader title="Cost breakdown" subtitle="Entered estimates (auction fees calculated separately)" />
        <CardBody className="p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-xs uppercase text-slate-500">
                <th className="px-5 py-2 font-medium">Item</th>
                <th className="px-5 py-2 font-medium">Category</th>
                <th className="px-5 py-2 font-medium">Min</th>
                <th className="px-5 py-2 font-medium">Estimated</th>
                <th className="px-5 py-2 font-medium">Max</th>
              </tr>
            </thead>
            <tbody>
              {appraisal.cost_items.map((c) => (
                <tr key={c.id} className="border-b border-slate-50">
                  <td className="px-5 py-2">{c.name}</td>
                  <td className="px-5 py-2"><Badge>{c.category}</Badge></td>
                  <td className="px-5 py-2">{formatGBP(c.minimum_amount)}</td>
                  <td className="px-5 py-2 font-medium">{formatGBP(c.estimated_amount)}</td>
                  <td className="px-5 py-2">{formatGBP(c.maximum_amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardBody>
      </Card>

      {/* Purchase confirmation modal */}
      {showPurchase && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
          <Card className="w-full max-w-md">
            <CardHeader title="Confirm purchase" subtitle="This converts the appraisal into a stock item." />
            <CardBody className="space-y-3">
              <Field label="Actual hammer price (£)">
                <Input value={hammer} onChange={(e) => setHammer(e.target.value)} />
              </Field>
              <p className="text-xs text-slate-500">
                Absolute maximum was {formatGBP(appraisal.absolute_max_bid)}. Buying above it erodes your target profit.
              </p>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={confirmChecked} onChange={(e) => setConfirmChecked(e.target.checked)} />
                I confirm this purchase and accept responsibility for the bidding decision.
              </label>
              {error && <p className="text-sm text-red-600">{error}</p>}
              <div className="flex justify-end gap-2">
                <Button variant="secondary" onClick={() => setShowPurchase(false)}>Cancel</Button>
                <Button disabled={!confirmChecked || busy} onClick={confirmPurchase}>
                  {busy ? "Recording…" : "Confirm purchase"}
                </Button>
              </div>
            </CardBody>
          </Card>
        </div>
      )}

      <p className="text-xs text-slate-400 print:hidden">Appraisal created {formatDate(appraisal.created_at)}, updated {formatDate(appraisal.updated_at)}.</p>
    </div>
  );
}
