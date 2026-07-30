"use client";

import { Plus, Trash2 } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AppraisalResult } from "@/components/appraisal-result";
import { Button, Card, CardBody, CardHeader, Field, Input, Spinner } from "@/components/ui";
import { DEFAULT_STATE, toPreviewRequest, type WizardState } from "@/features/appraisals/wizard-types";
import { api } from "@/lib/api";
import { formatGBP } from "@/lib/format";
import type { AuctionHouse, EvaluationResult, Listing } from "@/types";

const STEPS = ["Vehicle", "Auction", "History", "Valuation", "Costs", "Profit", "Result"];
const COST_CATEGORIES = ["SERVICE", "MECHANICAL", "BODYWORK", "TYRES", "MOT", "TRANSPORT", "VALETING", "DETAILING", "KEYS", "WARRANTY", "ADVERTISING", "STORAGE", "CONTINGENCY", "OTHER"];

export default function NewAppraisalPage() {
  const router = useRouter();
  const params = useSearchParams();
  const listingId = params.get("listing");

  const [step, setStep] = useState(0);
  const [s, setS] = useState<WizardState>(DEFAULT_STATE);
  const [houses, setHouses] = useState<AuctionHouse[]>([]);
  const [result, setResult] = useState<EvaluationResult | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [prefill, setPrefill] = useState<Listing | null>(null);

  const set = <K extends keyof WizardState>(k: K, v: WizardState[K]) => setS((p) => ({ ...p, [k]: v }));

  useEffect(() => {
    api.get<AuctionHouse[]>("/auction-houses").then(setHouses).catch(() => {});
  }, []);

  useEffect(() => {
    if (!listingId) return;
    api.get<Listing>(`/listings/${listingId}`).then((l) => {
      setPrefill(l);
      const v = l.vehicle;
      setS((p) => ({
        ...p,
        registration: v?.registration ?? "",
        make: v?.make ?? "",
        model: v?.model ?? "",
        derivative: v?.derivative ?? "",
        model_year: v?.model_year ? String(v.model_year) : "",
        mileage: v?.mileage ? String(v.mileage) : "",
        number_of_keys: v?.number_of_keys ? String(v.number_of_keys) : "2",
        category_marker: v?.category_marker ?? "",
        imported: v?.imported ?? false,
        auction_house_id: String(l.auction_house_id),
        lot_number: l.lot_number ?? "",
        guide_price: l.guide_price ?? "",
        current_bid: l.guide_price ?? "",
        condition_grade: l.condition_grade ? String(l.condition_grade) : "2",
        runner_status: l.runner_status ?? "RUNNER",
        vat_status: l.vat_status ?? "MARGIN",
        missing_service_history: v?.history?.service_history_status === "NONE",
        mileage_discrepancy: v?.history?.mileage_discrepancy ?? false,
      }));
    });
  }, [listingId]);

  const runPreview = useCallback(async () => {
    setPreviewing(true);
    setError(null);
    try {
      const res = await api.post<EvaluationResult>("/appraisals/preview", toPreviewRequest(s));
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Calculation failed");
    } finally {
      setPreviewing(false);
    }
  }, [s]);

  useEffect(() => {
    if (step === 6) runPreview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step]);

  async function fetchValuation() {
    if (!s.make || !s.model || !s.model_year) return;
    try {
      const data = await api.get<{ valuation: Record<string, number> }>("/lookups/valuation", {
        make: s.make, model: s.model, year: s.model_year, mileage: s.mileage || 0,
      });
      const v = data.valuation;
      setS((p) => ({
        ...p,
        expected_retail_price: String(v.estimated_retail),
        conservative_retail_price: String(v.cap_average),
        optimistic_retail_price: String(Math.round(v.estimated_retail * 1.05)),
      }));
    } catch { /* ignore */ }
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      let vehicleId: number;
      let auctionListingId: number | null = null;
      if (prefill) {
        vehicleId = prefill.vehicle_id;
        auctionListingId = prefill.id;
      } else {
        const vehicle = await api.post<{ id: number }>("/vehicles", {
          registration: s.registration || null,
          make: s.make, model: s.model, derivative: s.derivative || null,
          model_year: s.model_year ? Number(s.model_year) : null,
          mileage: s.mileage ? Number(s.mileage) : null,
          number_of_keys: Number(s.number_of_keys) || null,
          category_marker: s.category_marker || null,
          imported: s.imported,
        });
        vehicleId = vehicle.id;
        if (s.auction_house_id) {
          const listing = await api.post<{ id: number }>("/listings", {
            vehicle_id: vehicleId, auction_house_id: Number(s.auction_house_id),
            lot_number: s.lot_number || null, guide_price: s.guide_price || null,
            condition_grade: Number(s.condition_grade) || null, runner_status: s.runner_status,
            vat_status: s.vat_status,
          });
          auctionListingId = listing.id;
        }
      }
      const req = toPreviewRequest(s);
      const appraisal = await api.post<{ id: number }>("/appraisals", {
        vehicle_id: vehicleId,
        auction_listing_id: auctionListingId,
        expected_retail_price: req.expected_retail_price,
        conservative_retail_price: req.conservative_retail_price,
        optimistic_retail_price: req.optimistic_retail_price,
        expected_negotiated_discount: req.expected_negotiated_discount,
        pricing_confidence: s.pricing_confidence,
        target_profit: req.target_profit,
        risk_reserve: req.risk_reserve,
        desired_roi: req.desired_roi,
        estimated_days_to_sell: req.estimated_days_to_sell,
        current_bid: req.current_bid,
        status: "COMPLETE",
        cost_items: req.cost_items,
      });
      router.push(`/appraisals/${appraisal.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
      setSaving(false);
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">New appraisal</h1>
        <p className="text-sm text-slate-500">
          {prefill ? `${prefill.vehicle?.make} ${prefill.vehicle?.model} · Lot ${prefill.lot_number}` : "Manual entry"}
        </p>
      </div>

      {/* Stepper */}
      <ol className="flex flex-wrap gap-2 text-sm">
        {STEPS.map((label, i) => (
          <li key={label}>
            <button
              onClick={() => setStep(i)}
              className={`rounded-full px-3 py-1 ${i === step ? "bg-brand-600 text-white" : i < step ? "bg-brand-100 text-brand-700" : "bg-slate-100 text-slate-500"}`}
            >
              {i + 1}. {label}
            </button>
          </li>
        ))}
      </ol>

      {error && <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      <Card>
        <CardBody className="space-y-4">
          {step === 0 && (
            <div className="grid gap-3 md:grid-cols-3">
              <Field label="Registration" hint="Optional; validated when supplied">
                <Input value={s.registration} onChange={(e) => set("registration", e.target.value)} />
              </Field>
              <Field label="Make"><Input value={s.make} onChange={(e) => set("make", e.target.value)} /></Field>
              <Field label="Model"><Input value={s.model} onChange={(e) => set("model", e.target.value)} /></Field>
              <Field label="Derivative / trim"><Input value={s.derivative} onChange={(e) => set("derivative", e.target.value)} /></Field>
              <Field label="Year"><Input value={s.model_year} onChange={(e) => set("model_year", e.target.value)} /></Field>
              <Field label="Mileage"><Input value={s.mileage} onChange={(e) => set("mileage", e.target.value)} /></Field>
              <Field label="Number of keys"><Input value={s.number_of_keys} onChange={(e) => set("number_of_keys", e.target.value)} /></Field>
              <Field label="Category marker" hint="N, S, A or B (blank if none)">
                <Input value={s.category_marker} onChange={(e) => set("category_marker", e.target.value.toUpperCase())} />
              </Field>
            </div>
          )}

          {step === 1 && (
            <div className="grid gap-3 md:grid-cols-3">
              <Field label="Auction house">
                <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={s.auction_house_id} onChange={(e) => set("auction_house_id", e.target.value)}>
                  <option value="">Select…</option>
                  {houses.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
                </select>
              </Field>
              <Field label="Lot number"><Input value={s.lot_number} onChange={(e) => set("lot_number", e.target.value)} /></Field>
              <Field label="Guide price (£)"><Input value={s.guide_price} onChange={(e) => set("guide_price", e.target.value)} /></Field>
              <Field label="Current bid (£)"><Input value={s.current_bid} onChange={(e) => set("current_bid", e.target.value)} /></Field>
              <Field label="Condition grade" hint="1 (best) to 5 (worst)"><Input value={s.condition_grade} onChange={(e) => set("condition_grade", e.target.value)} /></Field>
              <Field label="Runner status">
                <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={s.runner_status} onChange={(e) => set("runner_status", e.target.value)}>
                  <option value="RUNNER">Runner</option>
                  <option value="NON_RUNNER">Non-runner</option>
                  <option value="UNKNOWN">Unknown</option>
                </select>
              </Field>
            </div>
          )}

          {step === 2 && (
            <div className="grid gap-3 md:grid-cols-3">
              <Field label="MOT fail count"><Input value={s.mot_fail_count} onChange={(e) => set("mot_fail_count", e.target.value)} /></Field>
              <Field label="Dangerous MOT defects"><Input value={s.dangerous_defect_count} onChange={(e) => set("dangerous_defect_count", e.target.value)} /></Field>
              <div className="space-y-2 pt-6">
                {[
                  ["mileage_discrepancy", "Mileage discrepancy"],
                  ["finance_marker", "Outstanding finance"],
                  ["stolen_marker", "Recorded as stolen"],
                  ["missing_service_history", "No service history"],
                  ["imported", "Imported vehicle"],
                ].map(([k, label]) => (
                  <label key={k} className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={s[k as keyof WizardState] as boolean} onChange={(e) => set(k as keyof WizardState, e.target.checked as never)} />
                    {label}
                  </label>
                ))}
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-3">
              <Button variant="secondary" onClick={fetchValuation}>Fetch demo valuation (mock adapter)</Button>
              <div className="grid gap-3 md:grid-cols-3">
                <Field label="Expected retail (£)"><Input value={s.expected_retail_price} onChange={(e) => set("expected_retail_price", e.target.value)} /></Field>
                <Field label="Conservative retail (£)"><Input value={s.conservative_retail_price} onChange={(e) => set("conservative_retail_price", e.target.value)} /></Field>
                <Field label="Optimistic retail (£)"><Input value={s.optimistic_retail_price} onChange={(e) => set("optimistic_retail_price", e.target.value)} /></Field>
                <Field label="Expected customer discount (£)"><Input value={s.expected_negotiated_discount} onChange={(e) => set("expected_negotiated_discount", e.target.value)} /></Field>
                <Field label="Pricing confidence">
                  <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={s.pricing_confidence} onChange={(e) => set("pricing_confidence", e.target.value)}>
                    <option value="HIGH">High</option><option value="MEDIUM">Medium</option><option value="LOW">Low</option>
                  </select>
                </Field>
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-3">
              {s.costs.map((c, i) => (
                <div key={i} className="grid grid-cols-2 gap-2 md:grid-cols-6">
                  <Input className="md:col-span-2" placeholder="Name" value={c.name} onChange={(e) => setS((p) => ({ ...p, costs: p.costs.map((x, j) => j === i ? { ...x, name: e.target.value } : x) }))} />
                  <select className="rounded-md border border-slate-300 px-2 text-sm" value={c.category} onChange={(e) => setS((p) => ({ ...p, costs: p.costs.map((x, j) => j === i ? { ...x, category: e.target.value } : x) }))}>
                    {COST_CATEGORIES.map((cat) => <option key={cat} value={cat}>{cat}</option>)}
                  </select>
                  <Input placeholder="Est" value={c.estimated_amount} onChange={(e) => setS((p) => ({ ...p, costs: p.costs.map((x, j) => j === i ? { ...x, estimated_amount: e.target.value } : x) }))} />
                  <Input placeholder="Min" value={c.minimum_amount} onChange={(e) => setS((p) => ({ ...p, costs: p.costs.map((x, j) => j === i ? { ...x, minimum_amount: e.target.value } : x) }))} />
                  <div className="flex gap-1">
                    <Input placeholder="Max" value={c.maximum_amount} onChange={(e) => setS((p) => ({ ...p, costs: p.costs.map((x, j) => j === i ? { ...x, maximum_amount: e.target.value } : x) }))} />
                    <button onClick={() => setS((p) => ({ ...p, costs: p.costs.filter((_, j) => j !== i) }))} className="text-slate-400 hover:text-red-600"><Trash2 size={16} /></button>
                  </div>
                </div>
              ))}
              <Button variant="secondary" onClick={() => setS((p) => ({ ...p, costs: [...p.costs, { name: "", category: "OTHER", estimated_amount: "0", minimum_amount: "", maximum_amount: "" }] }))}>
                <Plus size={16} /> Add cost
              </Button>
              <p className="text-xs text-slate-500">Auction buyer fees are calculated automatically from the auction house&apos;s fee bands.</p>
            </div>
          )}

          {step === 5 && (
            <div className="grid gap-3 md:grid-cols-2">
              <Field label="Target profit (£)"><Input value={s.target_profit} onChange={(e) => set("target_profit", e.target.value)} /></Field>
              <Field label="Minimum ROI (0-1)" hint="e.g. 0.15 = 15%"><Input value={s.desired_roi} onChange={(e) => set("desired_roi", e.target.value)} /></Field>
              <Field label="Risk reserve (£)"><Input value={s.risk_reserve} onChange={(e) => set("risk_reserve", e.target.value)} /></Field>
              <Field label="Expected days to sell"><Input value={s.estimated_days_to_sell} onChange={(e) => set("estimated_days_to_sell", e.target.value)} /></Field>
            </div>
          )}

          {step === 6 && (
            <div>
              {previewing ? <Spinner label="Calculating…" /> : result ? <AppraisalResult result={result} /> : <p className="text-sm text-slate-500">No result yet.</p>}
            </div>
          )}
        </CardBody>
      </Card>

      <div className="flex items-center justify-between">
        <Button variant="secondary" disabled={step === 0} onClick={() => setStep((x) => Math.max(0, x - 1))}>Back</Button>
        <div className="flex gap-2">
          {step === 6 ? (
            <>
              <Button variant="secondary" onClick={runPreview}>Recalculate</Button>
              <Button onClick={save} disabled={saving}>{saving ? "Saving…" : "Save appraisal"}</Button>
            </>
          ) : (
            <Button onClick={() => setStep((x) => Math.min(6, x + 1))}>Next</Button>
          )}
        </div>
      </div>

      {step === 6 && result?.calculation && (
        <p className="text-center text-sm text-slate-500">
          Reference hammer {formatGBP(result.calculation.reference_hammer)} · Safe max {formatGBP(result.calculation.safe_max_bid)} · Absolute max {formatGBP(result.calculation.absolute_max_bid)}
        </p>
      )}
    </div>
  );
}
