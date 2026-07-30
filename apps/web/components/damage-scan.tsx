"use client";

import { AlertTriangle, ExternalLink, Package, ScanSearch, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge, Button, Card, CardBody, CardHeader } from "@/components/ui";
import { useAuth } from "@/features/auth/auth-context";
import { api } from "@/lib/api";
import { formatGBP } from "@/lib/format";

interface DamageItem {
  panel: string;
  damage_type: string;
  severity: "MINOR" | "MODERATE" | "SEVERE";
  estimated_repair_min: number;
  estimated_repair_max: number;
  notes: string;
}
interface Analysis {
  analysis_source: string;
  images_analysed: number;
  disclaimer: string;
  costs_attached?: boolean;
  result: {
    overall_condition: string;
    confidence: string;
    summary: string;
    damage_items: DamageItem[];
    suggested_cost_items: Array<{ name: string; category: string; estimated_amount: number }>;
    recommended_checks: string[];
    advisor_notes: string;
  };
}

const SEV_TONE: Record<string, string> = { MINOR: "amber", MODERATE: "amber", SEVERE: "red" };

interface PartItem { title: string; price: number | null; currency: string; condition: string | null; url: string; image: string | null }
interface PartsResult { provider: string; groups: Array<{ panel: string; query: string; items: PartItem[] }>; disclaimer: string }

export function DamageScan({ appraisalId, onAttached }: { appraisalId: number; onAttached?: () => void }) {
  const { can } = useAuth();
  const [files, setFiles] = useState<FileList | null>(null);
  const [attach, setAttach] = useState(false);
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [provider, setProvider] = useState<{ provider: string; note: string; live: boolean } | null>(null);
  const [parts, setParts] = useState<PartsResult | null>(null);
  const [partsLoading, setPartsLoading] = useState(false);
  const [attaching, setAttaching] = useState(false);
  const [attachNote, setAttachNote] = useState<string | null>(null);

  async function attachParts() {
    if (!parts) return;
    setAttaching(true);
    setAttachNote(null);
    setError(null);
    try {
      const res = await api.post<{ added: unknown[]; recommendation: string }>(
        `/parts/attach/${appraisalId}`, { panels: parts.groups.map((g) => g.panel) });
      setAttachNote(`Added ${res.added.length} part cost(s) — recommendation now ${res.recommendation}.`);
      onAttached?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not add part costs");
    } finally {
      setAttaching(false);
    }
  }

  async function findParts() {
    if (!analysis) return;
    const panels = Array.from(new Set(analysis.result.damage_items.map((d) => d.panel))).slice(0, 4);
    if (!panels.length) return;
    setPartsLoading(true);
    setError(null);
    try {
      setParts(await api.post<PartsResult>("/parts/for-damage", { appraisal_id: appraisalId, panels }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Parts search failed");
    } finally {
      setPartsLoading(false);
    }
  }

  useEffect(() => {
    api.get<{ provider: string; note: string; live: boolean }>("/vision/status").then(setProvider).catch(() => {});
  }, []);

  async function scan() {
    if (!files || files.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      Array.from(files).forEach((f) => form.append("files", f));
      form.append("appraisal_id", String(appraisalId));
      form.append("attach_costs", attach ? "true" : "false");
      if (notes) form.append("notes", notes);
      const res = await api.post<Analysis>("/vision/damage", form);
      setAnalysis(res);
      setParts(null);
      if (res.costs_attached && onAttached) onAttached();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Scan failed");
    } finally {
      setBusy(false);
    }
  }

  if (!can("write")) return null;

  return (
    <Card>
      <CardHeader
        title={<span className="inline-flex items-center gap-2"><ScanSearch size={18} /> Photo damage scan</span>}
        subtitle="AI advisor assessment of visible damage from vehicle photos"
        action={provider && (
          <Badge tone={provider.live ? "green" : "slate"}>
            {provider.live ? "Claude vision" : "Demo (mock)"}
          </Badge>
        )}
      />
      <CardBody className="space-y-3">
        {provider && !provider.live && (
          <p className="rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-600">
            {provider.note} Set an Anthropic API key to analyse real photos with Claude.
          </p>
        )}

        <input type="file" accept="image/*" multiple onChange={(e) => setFiles(e.target.files)} className="text-sm" />
        <input
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Notes for the advisor (e.g. 'front bumper scuffed, check nearside')"
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={attach} onChange={(e) => setAttach(e.target.checked)} />
          Add the suggested repair costs to this appraisal and recalculate
        </label>
        <div>
          <Button onClick={scan} disabled={busy || !files?.length}>
            <Sparkles size={16} /> {busy ? "Analysing…" : "Scan photos"}
          </Button>
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}

        {analysis && (
          <div className="space-y-3 border-t border-slate-100 pt-3">
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <Badge tone={analysis.result.overall_condition === "POOR" ? "red" : "slate"}>
                Condition: {analysis.result.overall_condition}
              </Badge>
              <Badge tone={analysis.result.confidence === "HIGH" ? "green" : "amber"}>
                Confidence: {analysis.result.confidence}
              </Badge>
              <span className="text-slate-500">{analysis.images_analysed} photo(s)</span>
              {analysis.costs_attached && <Badge tone="green">Costs added</Badge>}
            </div>
            <p className="text-sm text-slate-700">{analysis.result.summary}</p>

            {analysis.result.damage_items.length > 0 && (
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
                    {analysis.result.damage_items.map((d, i) => (
                      <tr key={i} className="border-b border-slate-50">
                        <td className="py-1.5 pr-3 font-medium">{d.panel}</td>
                        <td className="py-1.5 pr-3 text-slate-600">{d.damage_type}<div className="text-xs text-slate-400">{d.notes}</div></td>
                        <td className="py-1.5 pr-3"><Badge tone={SEV_TONE[d.severity] || "slate"}>{d.severity}</Badge></td>
                        <td className="py-1.5 pr-3">{formatGBP(d.estimated_repair_min)}–{formatGBP(d.estimated_repair_max)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {analysis.result.recommended_checks.length > 0 && (
              <div>
                <p className="text-xs font-semibold uppercase text-slate-600">Recommended physical checks</p>
                <ul className="mt-1 space-y-1 text-sm text-slate-600">
                  {analysis.result.recommended_checks.map((c, i) => (
                    <li key={i} className="flex gap-1.5"><AlertTriangle size={14} className="mt-0.5 shrink-0 text-amber-500" />{c}</li>
                  ))}
                </ul>
              </div>
            )}

            {analysis.result.advisor_notes && (
              <p className="rounded-md bg-brand-50 px-3 py-2 text-sm text-brand-800">
                <strong>Advisor:</strong> {analysis.result.advisor_notes}
              </p>
            )}

            <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
              {analysis.disclaimer}
            </p>

            {/* Parts sourcing from eBay for the damaged panels */}
            {analysis.result.damage_items.length > 0 && (
              <div className="border-t border-slate-100 pt-3">
                <div className="flex items-center justify-between">
                  <p className="inline-flex items-center gap-1.5 text-sm font-semibold text-slate-800">
                    <Package size={16} /> Replacement parts
                  </p>
                  <Button variant="secondary" className="px-3 py-1 text-xs" disabled={partsLoading} onClick={findParts}>
                    {partsLoading ? "Searching…" : "Find parts on eBay"}
                  </Button>
                </div>

                {parts && (
                  <div className="mt-2 space-y-3">
                    <Badge tone={parts.provider === "EBAY" ? "green" : "slate"}>
                      {parts.provider === "EBAY" ? "Live eBay results" : "Demo results (add eBay keys)"}
                    </Badge>
                    {parts.groups.map((g) => (
                      <div key={g.panel}>
                        <p className="text-xs font-medium uppercase text-slate-500">{g.panel}</p>
                        <ul className="mt-1 space-y-1">
                          {g.items.map((it, i) => (
                            <li key={i} className="flex items-center justify-between gap-2 rounded-md border border-slate-100 px-3 py-1.5 text-sm">
                              <span className="truncate text-slate-700">{it.title}</span>
                              <span className="flex shrink-0 items-center gap-2">
                                {it.price != null && <span className="font-medium">{formatGBP(it.price)}</span>}
                                {it.condition && <span className="text-xs text-slate-400">{it.condition}</span>}
                                <a href={it.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-0.5 text-brand-700 hover:underline">
                                  View <ExternalLink size={12} />
                                </a>
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                    <div className="flex flex-wrap items-center gap-3">
                      <Button className="px-3 py-1 text-xs" disabled={attaching} onClick={attachParts}>
                        {attaching ? "Adding…" : "Add cheapest part per panel to costs"}
                      </Button>
                      {attachNote && <span className="text-xs text-emerald-700">{attachNote}</span>}
                    </div>
                    <p className="text-xs text-slate-500">{parts.disclaimer}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </CardBody>
    </Card>
  );
}
