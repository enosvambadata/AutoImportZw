"use client";

import { AlertTriangle, Camera, ClipboardPaste, FileSearch, Plus, Save, ScanSearch, Search, Sparkles, Trash2, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppraisalResult } from "@/components/appraisal-result";
import { Badge, Button, Card, CardBody, CardHeader, Field, Input, Spinner } from "@/components/ui";
import { DEFAULT_STATE, toPreviewRequest, type WizardState } from "@/features/appraisals/wizard-types";
import { api } from "@/lib/api";
import { formatDate, formatGBP } from "@/lib/format";
import type { AuctionHouse, EvaluationResult } from "@/types";

const COST_CATEGORIES = ["SERVICE", "MECHANICAL", "BODYWORK", "TYRES", "MOT", "TRANSPORT", "VALETING", "WARRANTY", "ADVERTISING", "CONTINGENCY", "OTHER"];

export default function EvaluatePage() {
  const router = useRouter();
  const [s, setS] = useState<WizardState>({ ...DEFAULT_STATE });
  const [houses, setHouses] = useState<AuctionHouse[]>([]);
  const [result, setResult] = useState<EvaluationResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [looking, setLooking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pasteText, setPasteText] = useState("");
  const [parsing, setParsing] = useState(false);
  const [parseNote, setParseNote] = useState<string | null>(null);
  const [damage, setDamage] = useState<Array<{ area: string; description: string; severity: string }>>([]);
  const [photos, setPhotos] = useState<FileList | null>(null);
  const [scanning, setScanning] = useState(false);
  const [scan, setScan] = useState<DamageScanResult | null>(null);
  const [scanAdded, setScanAdded] = useState<string | null>(null);
  const [vision, setVision] = useState<{ live: boolean; note: string } | null>(null);
  const [mot, setMot] = useState<MotData | null>(null);
  const [motNote, setMotNote] = useState<string | null>(null);
  const [motChecked, setMotChecked] = useState(false);

  const set = <K extends keyof WizardState>(k: K, v: WizardState[K]) => setS((p) => ({ ...p, [k]: v }));

  interface MotTest { date: string | null; result: string | null; odometer: number | null; unit: string | null; expiry: string | null; advisories: number; dangerous: number }
  interface MotData {
    data_source?: string; mot_expiry?: string | null;
    mot_pass_count?: number; mot_fail_count?: number; advisory_count?: number; dangerous_defect_count?: number;
    mot_tests?: MotTest[];
  }

  interface Parsed {
    source: string; make: string | null; model: string | null; derivative: string | null;
    model_year: number | null; mileage: number | null; category_marker: string | null;
    runner_status: string | null; guide_price: number | null; lot_number: string | null;
    description: string | null;
    damage_summary: string | null; damage_items: Array<{ area: string; description: string; severity: string }>;
    warnings: string[];
  }

  interface DamageScanResult {
    analysis_source: string; images_analysed: number; disclaimer: string;
    result: {
      overall_condition: string; confidence: string; summary: string;
      damage_items: Array<{ panel: string; damage_type: string; severity: string; estimated_repair_min: number; estimated_repair_max: number; notes: string }>;
      suggested_cost_items: Array<{ name: string; category: string; estimated_amount: number }>;
      recommended_checks: string[]; advisor_notes: string;
    };
  }

  async function parseListing() {
    if (pasteText.trim().length < 5) return;
    setParsing(true);
    setParseNote(null);
    setError(null);
    try {
      const d = await api.post<Parsed>("/listings/parse", { text: pasteText });
      setS((p) => ({
        ...p,
        make: d.make ?? p.make,
        model: d.model ?? p.model,
        derivative: d.derivative ?? p.derivative,
        model_year: d.model_year ? String(d.model_year) : p.model_year,
        mileage: d.mileage ? String(d.mileage) : p.mileage,
        category_marker: d.category_marker ?? p.category_marker,
        runner_status: d.runner_status && d.runner_status !== "UNKNOWN" ? d.runner_status : p.runner_status,
        guide_price: d.guide_price ? String(d.guide_price) : p.guide_price,
        lot_number: d.lot_number ?? p.lot_number,
        notes: d.description ?? p.notes,
      }));
      setDamage(d.damage_items || []);
      setParseNote(`${d.source === "CLAUDE" ? "Extracted by Claude" : "Extracted (basic parser)"}. ${d.damage_summary ?? "Review the fields and add the registration and photos."}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not read the listing");
    } finally {
      setParsing(false);
    }
  }

  useEffect(() => {
    api.get<AuctionHouse[]>("/auction-houses").then(setHouses).catch(() => {});
    api.get<{ live: boolean; note: string }>("/vision/status").then(setVision).catch(() => {});
  }, []);

  async function scanPhotos() {
    if (!photos?.length) return;
    setScanning(true);
    setError(null);
    setScanAdded(null);
    try {
      const form = new FormData();
      Array.from(photos).forEach((f) => form.append("files", f));
      if (s.notes) form.append("notes", s.notes);
      setScan(await api.post<DamageScanResult>("/vision/damage", form));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Photo scan failed");
    } finally {
      setScanning(false);
    }
  }

  function addScanCosts() {
    const items = scan?.result.suggested_cost_items ?? [];
    if (!items.length) return;
    setS((p) => ({
      ...p,
      costs: [...p.costs, ...items.map((c) => ({
        name: c.name, category: c.category || "BODYWORK",
        estimated_amount: String(c.estimated_amount ?? 0), minimum_amount: "", maximum_amount: "",
      }))],
    }));
    setScanAdded(`Added ${items.length} repair cost line(s) to the Costs section below.`);
  }

  async function lookup() {
    if (!s.registration.trim()) return;
    setLooking(true);
    setMotNote(null);
    setError(null);
    try {
      const res = await api.get<{
        identity: { make?: string; model?: string; model_year?: number; fuel_type?: string; colour?: string } | null;
        mot: MotData | null; disclaimer: string;
      }>("/lookups/registration", { reg: s.registration.trim() });
      const id = res.identity;
      const m = res.mot;
      const latestOdo = m?.mot_tests?.find((t) => t.odometer != null)?.odometer;
      setS((p) => ({
        ...p,
        make: id?.make ?? p.make,
        model: id?.model ?? p.model,
        model_year: id?.model_year ? String(id.model_year) : p.model_year,
        mileage: latestOdo != null ? String(latestOdo) : p.mileage,
      }));
      setMot(m);
      setMotChecked(true);
      setMotNote(res.disclaimer);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lookup failed");
    } finally { setLooking(false); }
  }

  async function fetchValuation() {
    if (!s.make || !s.model || !s.model_year) return;
    try {
      const data = await api.get<{ valuation: Record<string, number> }>("/lookups/valuation", { make: s.make, model: s.model, year: s.model_year, mileage: s.mileage || 0 });
      const v = data.valuation;
      setS((p) => ({ ...p, expected_retail_price: String(v.estimated_retail), conservative_retail_price: String(v.cap_average), optimistic_retail_price: String(Math.round(v.estimated_retail * 1.05)) }));
    } catch { /* ignore */ }
  }

  async function evaluate() {
    setBusy(true);
    setError(null);
    try {
      setResult(await api.post<EvaluationResult>("/appraisals/preview", toPreviewRequest(s)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Evaluation failed");
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const req = toPreviewRequest(s);
      const vehicle = await api.post<{ id: number }>("/vehicles", {
        registration: s.registration || null, make: s.make, model: s.model,
        derivative: s.derivative || null, model_year: s.model_year ? Number(s.model_year) : null,
        mileage: s.mileage ? Number(s.mileage) : null, category_marker: s.category_marker || null,
        notes: s.notes || null,
      });
      let listingId: number | null = null;
      if (s.auction_house_id) {
        const listing = await api.post<{ id: number }>("/listings", {
          vehicle_id: vehicle.id, auction_house_id: Number(s.auction_house_id),
          lot_number: s.lot_number || null, guide_price: s.guide_price || null,
          condition_grade: Number(s.condition_grade) || null, runner_status: s.runner_status,
          vat_status: s.vat_status,
        });
        listingId = listing.id;
      }
      const appraisal = await api.post<{ id: number }>("/appraisals", {
        vehicle_id: vehicle.id, auction_listing_id: listingId,
        expected_retail_price: req.expected_retail_price, conservative_retail_price: req.conservative_retail_price,
        optimistic_retail_price: req.optimistic_retail_price, expected_negotiated_discount: req.expected_negotiated_discount,
        pricing_confidence: s.pricing_confidence, target_profit: req.target_profit, risk_reserve: req.risk_reserve,
        desired_roi: req.desired_roi, estimated_days_to_sell: req.estimated_days_to_sell, current_bid: req.current_bid,
        status: "COMPLETE", cost_items: req.cost_items,
      });
      router.push(`/appraisals/${appraisal.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
      setSaving(false);
    }
  }

  return (
    <div className="space-y-5">
      <div className="rounded-2xl bg-gradient-to-br from-slate-800 to-brand-700 p-6 text-white shadow-sm">
        <h1 className="text-2xl font-bold">Evaluate a lot</h1>
        <p className="text-sm text-white/80">Enter a lot&apos;s details, evaluate it in memory, and only save if it&apos;s worth pursuing — nothing is stored until you click Save.</p>
      </div>

      <Card>
        <CardHeader
          title={<span className="inline-flex items-center gap-2"><FileSearch size={18} /> Step 1 · Check MOT history</span>}
          subtitle="Start every decision here — enter the registration and pull the DVSA MOT record before anything else"
          action={mot && (
            <Badge tone={mot.data_source === "DVSA_MOT" ? "green" : "slate"}>
              {mot.data_source === "DVSA_MOT" ? "DVSA — live" : "Demo (mock)"}
            </Badge>
          )}
        />
        <CardBody className="space-y-3">
          <div className="flex flex-wrap items-end gap-2">
            <div className="grow">
              <Field label="Registration">
                <Input value={s.registration} onChange={(e) => set("registration", e.target.value.toUpperCase())} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); lookup(); } }} placeholder="e.g. MF65 KHM" />
              </Field>
            </div>
            <Button disabled={looking || !s.registration} onClick={lookup}>
              <Search size={15} /> {looking ? "Checking…" : "Check MOT"}
            </Button>
          </div>
          {motNote && <p className="text-xs text-slate-500">{motNote}</p>}

          {motChecked && !mot && (
            <p className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900">No MOT record found for that registration. Check the plate, or the vehicle may be too new/exempt.</p>
          )}

          {mot && (
            <div className="space-y-3 border-t border-slate-100 pt-3">
              <dl className="grid grid-cols-2 gap-y-2 text-sm md:grid-cols-4">
                {(() => {
                  const expired = mot.mot_expiry ? new Date(mot.mot_expiry) < new Date() : null;
                  return [
                    ["MOT expiry", mot.mot_expiry ? `${formatDate(mot.mot_expiry)}${expired === false ? " · valid" : expired ? " · EXPIRED" : ""}` : "—"],
                    ["Tests", `${mot.mot_pass_count ?? 0} pass / ${mot.mot_fail_count ?? 0} fail`],
                    ["Advisories", String(mot.advisory_count ?? 0)],
                    ["Dangerous", String(mot.dangerous_defect_count ?? 0)],
                  ].map(([k, v]) => (
                    <div key={k}>
                      <dt className="text-xs uppercase text-slate-400">{k}</dt>
                      <dd className={`font-medium ${String(v).includes("EXPIRED") ? "text-red-600" : "text-slate-800"}`}>{v}</dd>
                    </div>
                  ));
                })()}
              </dl>

              {(mot.mot_tests?.length ?? 0) > 0 && (
                <div className="overflow-x-auto">
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
                      {mot.mot_tests!.map((t, i) => (
                        <tr key={i} className="border-b border-slate-50">
                          <td className="py-1.5 pr-3">{t.date ? formatDate(t.date) : "—"}</td>
                          <td className="py-1.5 pr-3"><Badge tone={t.result === "PASSED" ? "green" : t.result === "FAILED" ? "red" : "slate"}>{t.result ?? "—"}</Badge></td>
                          <td className="py-1.5 pr-3">{t.odometer != null ? `${new Intl.NumberFormat("en-GB").format(t.odometer)} ${t.unit ?? ""}`.trim() : "—"}</td>
                          <td className="py-1.5 pr-3">{t.expiry ? formatDate(t.expiry) : "—"}</td>
                          <td className="py-1.5 pr-3">{t.advisories} / <span className={t.dangerous ? "font-semibold text-red-600" : ""}>{t.dangerous}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <p className="text-xs text-slate-500">Make, model, year and latest mileage have been filled in below from this record. Continue to the next steps.</p>
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title={<span className="inline-flex items-center gap-2"><ClipboardPaste size={18} /> Step 2 · Paste a listing</span>}
          subtitle="Paste the listing text and let it fill the fields — then add the photos below"
        />
        <CardBody className="space-y-2">
          <textarea
            value={pasteText}
            onChange={(e) => setPasteText(e.target.value)}
            rows={4}
            placeholder="Paste the SYNETIQ / auction listing text here…"
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <div className="flex flex-wrap items-center gap-3">
            <Button variant="secondary" disabled={parsing || pasteText.trim().length < 5} onClick={parseListing}>
              <Sparkles size={16} /> {parsing ? "Reading…" : "Parse & fill"}
            </Button>
            {parseNote && <span className="text-xs text-slate-600">{parseNote}</span>}
          </div>
          {damage.length > 0 && (
            <div className="rounded-md bg-amber-50 p-2 text-xs text-amber-900">
              <span className="font-medium">Damage captured:</span>
              <ul className="mt-1 space-y-0.5">
                {damage.map((d, i) => <li key={i}>• {d.area}: {d.description} ({d.severity})</li>)}
              </ul>
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Vehicle & pricing" />
        <CardBody className="grid gap-3 md:grid-cols-3">
          <Field label="Registration">
            <Input value={s.registration} onChange={(e) => set("registration", e.target.value.toUpperCase())} placeholder="Checked in Step 1" />
          </Field>
          <Field label="Make"><Input value={s.make} onChange={(e) => set("make", e.target.value)} /></Field>
          <Field label="Model"><Input value={s.model} onChange={(e) => set("model", e.target.value)} /></Field>
          <Field label="Derivative"><Input value={s.derivative} onChange={(e) => set("derivative", e.target.value)} /></Field>
          <Field label="Year"><Input value={s.model_year} onChange={(e) => set("model_year", e.target.value)} /></Field>
          <Field label="Mileage"><Input value={s.mileage} onChange={(e) => set("mileage", e.target.value)} /></Field>
          <Field label="Auction house (for fees)">
            <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={s.auction_house_id} onChange={(e) => set("auction_house_id", e.target.value)}>
              <option value="">None</option>
              {houses.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
            </select>
          </Field>
          <Field label="Guide price (£)"><Input value={s.guide_price} onChange={(e) => set("guide_price", e.target.value)} /></Field>
          <Field label="Current bid (£)"><Input value={s.current_bid} onChange={(e) => set("current_bid", e.target.value)} /></Field>
          <Field label="Category (N/S/A/B)"><Input value={s.category_marker} onChange={(e) => set("category_marker", e.target.value.toUpperCase())} /></Field>
          <Field label="Runner status">
            <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={s.runner_status} onChange={(e) => set("runner_status", e.target.value)}>
              <option value="RUNNER">Runner</option><option value="NON_RUNNER">Non-runner</option><option value="UNKNOWN">Unknown</option>
            </select>
          </Field>
          <div className="md:col-span-3">
            <Field label="Description / notes (from listing)">
              <textarea
                value={s.notes}
                onChange={(e) => set("notes", e.target.value)}
                rows={3}
                placeholder="Seller description — condition, MOT, history, faults, extras…"
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </Field>
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title={<span className="inline-flex items-center gap-2"><Camera size={18} /> Step 3 · Photos & damage scan</span>}
          subtitle="Upload the vehicle photos — the advisor assesses visible damage and suggests repair costs"
          action={vision && <Badge tone={vision.live ? "green" : "slate"}>{vision.live ? "Claude vision" : "Demo (mock)"}</Badge>}
        />
        <CardBody className="space-y-3">
          {vision && !vision.live && (
            <p className="rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-600">
              {vision.note} Add an Anthropic API key to analyse real photos with Claude.
            </p>
          )}
          <input type="file" accept="image/*" multiple onChange={(e) => setPhotos(e.target.files)} className="text-sm" />
          <div className="flex flex-wrap items-center gap-3">
            <Button variant="secondary" disabled={scanning || !photos?.length} onClick={scanPhotos}>
              <ScanSearch size={16} /> {scanning ? "Analysing…" : "Scan photos"}
            </Button>
            <span className="text-xs text-slate-500">Photos are used for the assessment only — they are not stored. The suggested costs are.</span>
          </div>

          {scan && (
            <div className="space-y-3 border-t border-slate-100 pt-3">
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <Badge tone={scan.result.overall_condition === "POOR" ? "red" : "slate"}>Condition: {scan.result.overall_condition}</Badge>
                <Badge tone={scan.result.confidence === "HIGH" ? "green" : "amber"}>Confidence: {scan.result.confidence}</Badge>
                <span className="text-slate-500">{scan.images_analysed} photo(s)</span>
              </div>
              <p className="text-sm text-slate-700">{scan.result.summary}</p>

              {scan.result.damage_items.length > 0 && (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-100 text-left text-xs uppercase text-slate-500">
                        <th className="py-1 pr-3 font-medium">Panel</th>
                        <th className="py-1 pr-3 font-medium">Damage</th>
                        <th className="py-1 pr-3 font-medium">Severity</th>
                        <th className="py-1 pr-3 font-medium">Est. repair</th>
                      </tr>
                    </thead>
                    <tbody>
                      {scan.result.damage_items.map((d, i) => (
                        <tr key={i} className="border-b border-slate-50">
                          <td className="py-1.5 pr-3 font-medium">{d.panel}</td>
                          <td className="py-1.5 pr-3 text-slate-600">{d.damage_type}<div className="text-xs text-slate-400">{d.notes}</div></td>
                          <td className="py-1.5 pr-3"><Badge tone={d.severity === "SEVERE" ? "red" : "amber"}>{d.severity}</Badge></td>
                          <td className="py-1.5 pr-3">{formatGBP(d.estimated_repair_min)}–{formatGBP(d.estimated_repair_max)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {scan.result.recommended_checks.length > 0 && (
                <ul className="space-y-1 text-sm text-slate-600">
                  {scan.result.recommended_checks.map((c, i) => (
                    <li key={i} className="flex gap-1.5"><AlertTriangle size={14} className="mt-0.5 shrink-0 text-amber-500" />{c}</li>
                  ))}
                </ul>
              )}
              {scan.result.advisor_notes && (
                <p className="rounded-md bg-brand-50 px-3 py-2 text-sm text-brand-800"><strong>Advisor:</strong> {scan.result.advisor_notes}</p>
              )}

              <div className="flex flex-wrap items-center gap-3">
                <Button className="px-3 py-1 text-xs" disabled={!scan.result.suggested_cost_items.length} onClick={addScanCosts}>
                  <Plus size={14} /> Add suggested repair costs to evaluation
                </Button>
                {scanAdded && <span className="text-xs text-emerald-700">{scanAdded}</span>}
              </div>
              <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">{scan.disclaimer}</p>
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Valuation & profit" action={<Button variant="ghost" className="text-xs" onClick={fetchValuation}>Fetch valuation</Button>} />
        <CardBody className="grid gap-3 md:grid-cols-3">
          <Field label="Expected retail (£)"><Input value={s.expected_retail_price} onChange={(e) => set("expected_retail_price", e.target.value)} /></Field>
          <Field label="Conservative retail (£)"><Input value={s.conservative_retail_price} onChange={(e) => set("conservative_retail_price", e.target.value)} /></Field>
          <Field label="Optimistic retail (£)"><Input value={s.optimistic_retail_price} onChange={(e) => set("optimistic_retail_price", e.target.value)} /></Field>
          <Field label="Customer discount (£)"><Input value={s.expected_negotiated_discount} onChange={(e) => set("expected_negotiated_discount", e.target.value)} /></Field>
          <Field label="Target profit (£)"><Input value={s.target_profit} onChange={(e) => set("target_profit", e.target.value)} /></Field>
          <Field label="Min ROI (0-1)"><Input value={s.desired_roi} onChange={(e) => set("desired_roi", e.target.value)} /></Field>
          <Field label="Risk reserve (£)"><Input value={s.risk_reserve} onChange={(e) => set("risk_reserve", e.target.value)} /></Field>
          <Field label="Days to sell"><Input value={s.estimated_days_to_sell} onChange={(e) => set("estimated_days_to_sell", e.target.value)} /></Field>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Costs" subtitle="Auction fees are calculated automatically from the chosen house" />
        <CardBody className="space-y-2">
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
          <Button variant="secondary" onClick={() => setS((p) => ({ ...p, costs: [...p.costs, { name: "", category: "OTHER", estimated_amount: "0", minimum_amount: "", maximum_amount: "" }] }))}><Plus size={16} /> Add cost</Button>
        </CardBody>
      </Card>

      {error && <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      <div className="flex flex-wrap items-center justify-between gap-2">
        <Button onClick={evaluate} disabled={busy || !s.make || !s.model}><Sparkles size={16} /> {busy ? "Evaluating…" : "Evaluate"}</Button>
        {result && (
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => { setResult(null); setS({ ...DEFAULT_STATE }); }}><X size={16} /> Discard</Button>
            <Button onClick={save} disabled={saving}><Save size={16} /> {saving ? "Saving…" : "Save appraisal"}</Button>
          </div>
        )}
      </div>

      {busy ? <Spinner label="Evaluating…" /> : result && (
        <div>
          {result.calculation && (
            <p className="mb-3 text-center text-sm text-slate-500">
              In-memory evaluation — nothing saved yet. Safe max {formatGBP(result.calculation.safe_max_bid)} · Absolute max {formatGBP(result.calculation.absolute_max_bid)}.
            </p>
          )}
          <AppraisalResult result={result} />
        </div>
      )}
    </div>
  );
}
