"use client";

import { ExternalLink, ImagePlus, Store, X } from "lucide-react";
import { useState } from "react";

import { Badge, Button, Card, CardBody, CardHeader, Field, Input } from "@/components/ui";
import { useAuth } from "@/features/auth/auth-context";
import { api } from "@/lib/api";

const COST_FIELDS: Array<[string, string]> = [
  ["vehicle_price", "Vehicle price"],
  ["auction_fees", "Auction fees"],
  ["uk_transport", "UK transport"],
  ["ocean_freight", "Ocean freight"],
  ["inland_transport", "Inland transport"],
  ["import_duty", "Customs duty"],
  ["import_surtax", "Surtax"],
  ["import_vat", "VAT"],
  ["estimated_repairs", "Est. repairs"],
  ["service_fee", "Service fee"],
];
// Fields that make up the Value-for-Duty (CIF) base for the ZIMRA duty calc.
const VDP_FIELDS = ["vehicle_price", "auction_fees", "uk_transport", "ocean_freight", "inland_transport"];

const DUTY_CATEGORIES: Array<[string, string]> = [
  ["CAR", "Passenger car (40%, +35% surtax)"],
  ["SUV", "SUV / 4x4 (60%, +35% surtax)"],
  ["DOUBLE_CAB", "Double cab (60%, no surtax)"],
  ["SINGLE_CAB", "Single cab / pickup (40%, no surtax)"],
  ["LIGHT_TRUCK", "Light truck <5t (40%, no surtax)"],
  ["HEAVY_TRUCK", "Heavy truck ≥5t (25%, no surtax)"],
];

export function StorefrontPublish({ vehicleId, appraisalId, suggestedHeadline }: {
  vehicleId: number; appraisalId?: number; suggestedHeadline: string;
}) {
  const { can } = useAuth();
  const [open, setOpen] = useState(false);
  const [headline, setHeadline] = useState(suggestedHeadline);
  const [blurb, setBlurb] = useState("");
  const [videoUrl, setVideoUrl] = useState("");
  const [destPort, setDestPort] = useState("Walvis Bay");
  const [destCity, setDestCity] = useState("Harare");
  const [costs, setCosts] = useState<Record<string, string>>(Object.fromEntries(COST_FIELDS.map(([k]) => [k, "0"])));
  const [category, setCategory] = useState("CAR");
  const [over5, setOver5] = useState(true);
  const [dutyNote, setDutyNote] = useState<string | null>(null);
  const [images, setImages] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [slug, setSlug] = useState<string | null>(null);

  if (!can("write")) return null;

  async function uploadPhotos(files: FileList | null) {
    if (!files || files.length === 0) return;
    setUploading(true); setError(null);
    try {
      const form = new FormData();
      form.append("key", `veh-${vehicleId}`);
      Array.from(files).forEach((f) => form.append("files", f));
      const res = await api.post<{ urls: string[] }>("/storefront/upload", form);
      setImages((p) => [...p, ...res.urls]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally { setUploading(false); }
  }

  async function calcDuty() {
    const vdp = VDP_FIELDS.reduce((s, k) => s + (Number(costs[k]) || 0), 0);
    if (vdp <= 0) { setError("Enter the vehicle price and freight first, then calculate duty."); return; }
    setDutyNote(null); setError(null);
    try {
      const surtaxCat = category === "CAR" || category === "SUV";
      const q = await api.post<{ vdp: string; customs_duty: string; surtax: string; vat: string; total_taxes: string }>(
        "/storefront/duty-quote", { vdp, category, surtax_applies: surtaxCat && over5 });
      setCosts((p) => ({ ...p, import_duty: q.customs_duty, import_surtax: q.surtax, import_vat: q.vat }));
      setDutyNote(`ZIMRA on CIF $${Number(q.vdp).toLocaleString()} → duty $${Number(q.customs_duty).toLocaleString()} + surtax $${Number(q.surtax).toLocaleString()} + VAT $${Number(q.vat).toLocaleString()} = $${Number(q.total_taxes).toLocaleString()}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Duty calculation failed");
    }
  }

  async function publish(status: "DRAFT" | "PUBLISHED") {
    setBusy(true); setError(null);
    try {
      const body: Record<string, unknown> = {
        vehicle_id: vehicleId, appraisal_id: appraisalId ?? null, headline, blurb: blurb || null,
        video_url: videoUrl || null, image_urls: images, currency: "USD", status,
        dest_port: destPort || null, dest_city: destCity || null,
      };
      for (const [k] of COST_FIELDS) body[k] = costs[k] || "0";
      const res = await api.post<{ slug: string }>("/storefront/listings", body);
      setSlug(res.slug);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Publish failed");
    } finally { setBusy(false); }
  }

  const total = COST_FIELDS.reduce((s, [k]) => s + (Number(costs[k]) || 0), 0);

  return (
    <Card>
      <CardHeader
        title={<span className="inline-flex items-center gap-2"><Store size={18} /> Storefront</span>}
        subtitle="Publish this car to the public import storefront with a USD landed cost"
        action={<Button variant="ghost" className="text-xs" onClick={() => setOpen((o) => !o)}>{open ? "Hide" : "Publish to storefront"}</Button>}
      />
      {open && (
        <CardBody className="space-y-3">
          {slug ? (
            <div className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-900">
              <p className="font-medium">Published.</p>
              <a href={`/store/car/${slug}`} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-brand-700 underline">
                View public page <ExternalLink size={13} />
              </a>
            </div>
          ) : (
            <>
              <div className="grid gap-3 md:grid-cols-2">
                <Field label="Headline"><Input value={headline} onChange={(e) => setHeadline(e.target.value)} /></Field>
                <Field label="Video URL (YouTube/Vimeo, optional)"><Input value={videoUrl} onChange={(e) => setVideoUrl(e.target.value)} placeholder="https://youtu.be/…" /></Field>
              </div>
              <Field label="Condition blurb (public, honest)">
                <textarea value={blurb} onChange={(e) => setBlurb(e.target.value)} rows={2} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
              </Field>

              <div>
                <div className="mb-1.5 flex items-center gap-3">
                  <label className="inline-flex cursor-pointer items-center gap-1.5 rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium hover:bg-slate-50">
                    <ImagePlus size={15} /> {uploading ? "Uploading…" : "Upload photos"}
                    <input type="file" accept="image/*" multiple className="hidden" disabled={uploading}
                           onChange={(e) => { uploadPhotos(e.target.files); e.target.value = ""; }} />
                  </label>
                  <span className="text-xs text-slate-500">{images.length ? `${images.length} photo(s) attached` : "JPG/PNG/WebP · up to 24"}</span>
                </div>
                {images.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {images.map((src, i) => (
                      <div key={src} className="relative h-16 w-20 overflow-hidden rounded border border-slate-200">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={src} alt="" className="h-full w-full object-cover" />
                        <button onClick={() => setImages((p) => p.filter((_, j) => j !== i))} className="absolute right-0 top-0 bg-black/60 p-0.5 text-white" aria-label="Remove"><X size={11} /></button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="grid gap-3 md:grid-cols-4">
                {COST_FIELDS.map(([k, label]) => (
                  <Field key={k} label={`${label} (USD)`}>
                    <Input value={costs[k]} onChange={(e) => setCosts((p) => ({ ...p, [k]: e.target.value.replace(/[^\d.]/g, "") }))} />
                  </Field>
                ))}
                <Field label="Dest. port"><Input value={destPort} onChange={(e) => setDestPort(e.target.value)} /></Field>
                <Field label="Dest. city"><Input value={destCity} onChange={(e) => setDestCity(e.target.value)} /></Field>
              </div>
              <div className="flex flex-wrap items-center gap-3 rounded-md bg-slate-50 p-2">
                <select value={category} onChange={(e) => setCategory(e.target.value)} className="rounded-md border border-slate-300 px-2 py-1.5 text-xs">
                  {DUTY_CATEGORIES.map(([k, label]) => <option key={k} value={k}>{label}</option>)}
                </select>
                <Button variant="secondary" className="text-xs" onClick={calcDuty}>Calculate ZIM duty</Button>
                {(category === "CAR" || category === "SUV") && (
                  <label className="flex items-center gap-1.5 text-xs text-slate-600">
                    <input type="checkbox" checked={over5} onChange={(e) => setOver5(e.target.checked)} /> Over 5 years old (adds 35% surtax)
                  </label>
                )}
                {dutyNote && <span className="w-full text-xs text-emerald-700">{dutyNote}</span>}
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <Badge tone="slate">Landed total: USD {total.toLocaleString("en-US")}</Badge>
                <Button variant="secondary" disabled={busy} onClick={() => publish("DRAFT")}>Save draft</Button>
                <Button disabled={busy || headline.trim().length < 3} onClick={() => publish("PUBLISHED")}>{busy ? "Publishing…" : "Publish live"}</Button>
              </div>
              {error && <p className="text-sm text-red-600">{error}</p>}
            </>
          )}
        </CardBody>
      )}
    </Card>
  );
}
