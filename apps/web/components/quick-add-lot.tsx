"use client";

import { Plus, Search, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button, Card, CardBody, CardHeader, Field, Input } from "@/components/ui";
import { api } from "@/lib/api";

interface RegLookup {
  identity: {
    make?: string;
    model?: string;
    model_year?: number;
    fuel_type?: string;
    transmission?: string;
    colour?: string;
  } | null;
  provenance: string;
}

const EMPTY = {
  registration: "", make: "", model: "", derivative: "", model_year: "", mileage: "",
  guide_price: "", lot_number: "", auction_house: "SYNETIQ", category_marker: "",
};

export function QuickAddLot({ onAdded }: { onAdded?: () => void }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ ...EMPTY });
  const [busy, setBusy] = useState(false);
  const [looking, setLooking] = useState(false);
  const [lookupNote, setLookupNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const set = (k: keyof typeof EMPTY, v: string) => setF((p) => ({ ...p, [k]: v }));

  async function lookup() {
    if (!f.registration.trim()) return;
    setLooking(true);
    setLookupNote(null);
    setError(null);
    try {
      const res = await api.get<RegLookup>("/lookups/registration", { reg: f.registration.trim() });
      const id = res.identity;
      if (!id) {
        setLookupNote("No details found for that registration.");
        return;
      }
      setF((p) => ({
        ...p,
        make: id.make ?? p.make,
        model: id.model ?? p.model,
        model_year: id.model_year ? String(id.model_year) : p.model_year,
        derivative: p.derivative,
      }));
      setLookupNote(
        res.provenance === "MOCK_ADAPTER"
          ? "Auto-filled from demo data (add DVLA/DVSA keys for real details)."
          : "Auto-filled from DVLA/DVSA.",
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Look-up failed");
    } finally {
      setLooking(false);
    }
  }

  async function submit(appraise: boolean) {
    setBusy(true);
    setError(null);
    try {
      const created = await api.post<{ id: number }>("/listings/quick-add", {
        make: f.make,
        model: f.model,
        registration: f.registration || null,
        derivative: f.derivative || null,
        model_year: f.model_year ? Number(f.model_year) : null,
        mileage: f.mileage ? Number(f.mileage) : null,
        guide_price: f.guide_price || null,
        lot_number: f.lot_number || null,
        auction_house: f.auction_house || "SYNETIQ",
        category_marker: f.category_marker || null,
      });
      setOpen(false);
      setF({ ...EMPTY });
      if (appraise) router.push(`/appraisals/new?listing=${created.id}`);
      else onAdded?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not add lot");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Button variant="secondary" className="bg-white/15 text-white hover:bg-white/25 border-white/20" onClick={() => setOpen(true)}>
        <Plus size={16} /> Quick add lot
      </Button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
          <Card className="w-full max-w-lg">
            <CardHeader
              title="Quick add a lot"
              subtitle="Key a lot you're watching (e.g. from SYNETIQ's site) into your catalogue"
              action={<button onClick={() => setOpen(false)} aria-label="Close" className="rounded-md p-1 text-slate-500 hover:bg-slate-100"><X size={18} /></button>}
            />
            <CardBody className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Make"><Input value={f.make} onChange={(e) => set("make", e.target.value)} /></Field>
                <Field label="Model"><Input value={f.model} onChange={(e) => set("model", e.target.value)} /></Field>
                <Field label="Registration" hint={lookupNote ?? "Type a plate and look up the details"}>
                  <div className="flex gap-2">
                    <Input value={f.registration} onChange={(e) => set("registration", e.target.value.toUpperCase())}
                           onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); lookup(); } }} />
                    <Button variant="secondary" className="shrink-0 px-3" disabled={looking || !f.registration} onClick={lookup}>
                      <Search size={15} /> {looking ? "…" : "Look up"}
                    </Button>
                  </div>
                </Field>
                <Field label="Derivative / trim"><Input value={f.derivative} onChange={(e) => set("derivative", e.target.value)} /></Field>
                <Field label="Year"><Input value={f.model_year} onChange={(e) => set("model_year", e.target.value)} /></Field>
                <Field label="Mileage"><Input value={f.mileage} onChange={(e) => set("mileage", e.target.value)} /></Field>
                <Field label="Guide price (£)"><Input value={f.guide_price} onChange={(e) => set("guide_price", e.target.value)} /></Field>
                <Field label="Lot number"><Input value={f.lot_number} onChange={(e) => set("lot_number", e.target.value)} /></Field>
                <Field label="Auction house"><Input value={f.auction_house} onChange={(e) => set("auction_house", e.target.value)} /></Field>
                <Field label="Category (N/S/A/B)"><Input value={f.category_marker} onChange={(e) => set("category_marker", e.target.value.toUpperCase())} /></Field>
              </div>
              {error && <p className="text-sm text-red-600">{error}</p>}
              <div className="flex justify-end gap-2">
                <Button variant="secondary" disabled={busy || !f.make || !f.model} onClick={() => submit(false)}>Add to catalogue</Button>
                <Button disabled={busy || !f.make || !f.model} onClick={() => submit(true)}>{busy ? "Adding…" : "Add & appraise"}</Button>
              </div>
            </CardBody>
          </Card>
        </div>
      )}
    </>
  );
}
