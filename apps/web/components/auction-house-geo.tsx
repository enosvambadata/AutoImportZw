"use client";

import { MapPin } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Button, Input } from "@/components/ui";
import { api } from "@/lib/api";
import { formatGBP } from "@/lib/format";

interface Transport {
  miles: number | null;
  estimated_transport: number | null;
  note?: string;
}

export function AuctionHouseGeo({ id, postcode, editable }: { id: number; postcode: string | null; editable: boolean }) {
  const [pc, setPc] = useState(postcode ?? "");
  const [dist, setDist] = useState<Transport | null>(null);
  const [saving, setSaving] = useState(false);

  const loadDist = useCallback(() => {
    api.get<Transport>(`/geo/auction-transport/${id}`).then(setDist).catch(() => {});
  }, [id]);

  useEffect(() => { loadDist(); }, [loadDist]);

  async function save() {
    setSaving(true);
    try {
      await api.patch(`/auction-houses/${id}`, { postcode: pc || null });
      loadDist();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-600">
      <MapPin size={13} className="text-slate-400" />
      {editable ? (
        <>
          <Input value={pc} onChange={(e) => setPc(e.target.value.toUpperCase())}
                 className="h-7 w-32 py-1 text-xs" placeholder="Site postcode" />
          <Button variant="secondary" className="px-2 py-1 text-xs" disabled={saving} onClick={save}>
            {saving ? "…" : "Save"}
          </Button>
        </>
      ) : postcode ? (
        <span>{postcode}</span>
      ) : (
        <span className="text-slate-400">No postcode set</span>
      )}
      {dist?.miles != null && (
        <span className="rounded bg-slate-100 px-2 py-0.5">
          ≈ {dist.miles} mi away · transport ≈ {formatGBP(dist.estimated_transport)}
        </span>
      )}
    </div>
  );
}
