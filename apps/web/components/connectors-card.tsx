"use client";

import { useEffect, useState } from "react";

import { Badge, Button, Card, CardBody, CardHeader } from "@/components/ui";
import { api } from "@/lib/api";

interface Connector {
  name: string;
  kind: string;
  source: string;
  configured: boolean;
  demo: boolean;
}

export function ConnectorsCard() {
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    api.get<{ connectors: Connector[] }>("/connectors").then((d) => setConnectors(d.connectors)).catch(() => {});
  }
  useEffect(load, []);

  async function sync(name: string) {
    setBusy(name);
    setMessage(null);
    setError(null);
    try {
      const r = await api.post<{ listings_created: number; listings_updated: number; source: string }>(
        `/connectors/${name}/sync`,
      );
      setMessage(`${r.source}: ${r.listings_created} new, ${r.listings_updated} updated listing(s).`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sync failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card>
      <CardHeader
        title="Data connectors"
        subtitle="Ingest auction catalogues and live pricing from official provider APIs"
      />
      <CardBody className="space-y-3">
        {connectors.map((c) => (
          <div key={c.name} className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-slate-100 p-3">
            <div>
              <p className="font-medium capitalize text-slate-800">{c.name}</p>
              <p className="text-xs text-slate-500">{c.kind} · {c.source}</p>
            </div>
            <div className="flex items-center gap-2">
              <Badge tone={c.configured ? "green" : "slate"}>
                {c.demo ? "Demo" : c.configured ? "Configured" : "Not configured"}
              </Badge>
              {c.kind === "catalogue" && c.configured && (
                <Button variant="secondary" className="px-3 py-1 text-xs" disabled={busy === c.name} onClick={() => sync(c.name)}>
                  {busy === c.name ? "Syncing…" : "Sync now"}
                </Button>
              )}
            </div>
          </div>
        ))}
        {message && <p className="text-sm text-emerald-700">{message}</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        <p className="text-xs text-slate-500">
          Copart, SYNETIQ and Auto Trader require an official API account and credentials (set their env
          vars). The demo connector is always available so the ingestion pipeline can be exercised. The
          platform never scrapes provider websites.
        </p>
      </CardBody>
    </Card>
  );
}
