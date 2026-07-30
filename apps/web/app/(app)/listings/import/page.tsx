"use client";

import { CheckCircle2, Download, Upload } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Badge, Button, Card, CardBody, CardHeader, Field, Input } from "@/components/ui";
import { api } from "@/lib/api";

interface ImportRow {
  row: number;
  data: Record<string, string>;
  errors: string[];
  is_duplicate: boolean;
  importable: boolean;
}
interface ImportResult {
  profile: string;
  headers: string[];
  unknown_columns: string[];
  rows: ImportRow[];
  summary: { total: number; valid: number; with_errors: number; duplicates: number };
}
interface CommitResult {
  ingested: number;
  vehicles_created: number;
  listings_created: number;
  listings_updated: number;
}

const PROFILES = [
  { value: "synetiq", label: "SYNETIQ export" },
  { value: "copart", label: "Copart export" },
  { value: "generic", label: "Generic / template" },
];

export default function ImportPage() {
  const [profile, setProfile] = useState("synetiq");
  const [house, setHouse] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [committed, setCommitted] = useState<CommitResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function preview(f: File) {
    setBusy(true);
    setError(null);
    setCommitted(null);
    try {
      const form = new FormData();
      form.append("file", f);
      form.append("profile", profile);
      setResult(await api.post<ImportResult>("/imports/preview", form));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Preview failed");
    } finally {
      setBusy(false);
    }
  }

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    await preview(f);
  }

  async function commit() {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("profile", profile);
      if (house) form.append("auction_house", house);
      setCommitted(await api.post<CommitResult>("/imports/commit", form));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setBusy(false);
    }
  }

  async function downloadTemplate() {
    const res = await api.raw("/imports/template", { method: "GET" });
    const text = await res.text();
    const blob = new Blob([text], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "autobid_catalogue_template.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Import catalogue</h1>
          <p className="text-sm text-slate-500">
            Upload your own account export (e.g. a SYNETIQ catalogue download) — preview, then import.
          </p>
        </div>
        <Button variant="secondary" onClick={downloadTemplate}><Download size={16} /> Template</Button>
      </div>

      <Card>
        <CardBody className="grid gap-3 md:grid-cols-3">
          <Field label="Source format">
            <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={profile}
                    onChange={(e) => { setProfile(e.target.value); if (file) preview(file); }}>
              {PROFILES.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
            </select>
          </Field>
          <Field label="Auction house (optional override)" hint="Used when a row has no location column">
            <Input value={house} onChange={(e) => setHouse(e.target.value)} placeholder="e.g. SYNETIQ Doncaster" />
          </Field>
          <Field label="CSV file">
            <input type="file" accept=".csv" onChange={onUpload} className="mt-1.5 text-sm" />
          </Field>
        </CardBody>
      </Card>

      {busy && <p className="text-sm text-slate-500">Working…</p>}
      {error && <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      {committed && (
        <Card>
          <CardBody className="flex flex-wrap items-center justify-between gap-3">
            <p className="inline-flex items-center gap-2 text-sm font-medium text-emerald-700">
              <CheckCircle2 size={18} /> Imported {committed.listings_created} new and updated {committed.listings_updated} listing(s).
            </p>
            <Link href="/listings"><Button>View listings</Button></Link>
          </CardBody>
        </Card>
      )}

      {result && !committed && (
        <>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <Badge tone="slate">{result.summary.total} rows</Badge>
            <Badge tone="green">{result.summary.valid} importable</Badge>
            <Badge tone="red">{result.summary.with_errors} with errors</Badge>
            <Badge tone="amber">{result.summary.duplicates} duplicates</Badge>
            <div className="ml-auto">
              <Button onClick={commit} disabled={busy || result.summary.valid === 0}>
                <Upload size={16} /> Import {result.summary.valid} valid row(s)
              </Button>
            </div>
          </div>
          {result.unknown_columns.length > 0 && (
            <p className="text-xs text-amber-700">Unrecognised columns ignored: {result.unknown_columns.join(", ")}</p>
          )}
          <Card>
            <CardHeader title="Preview" subtitle="Rows with errors or duplicates are flagged and skipped on import." />
            <CardBody className="overflow-x-auto p-0">
              <table className="w-full min-w-[720px] text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-left text-xs uppercase text-slate-500">
                    <th className="px-4 py-2 font-medium">Row</th>
                    <th className="px-4 py-2 font-medium">Vehicle</th>
                    <th className="px-4 py-2 font-medium">Lot</th>
                    <th className="px-4 py-2 font-medium">Guide</th>
                    <th className="px-4 py-2 font-medium">Cat</th>
                    <th className="px-4 py-2 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {result.rows.map((r) => (
                    <tr key={r.row} className={`border-b border-slate-50 ${r.errors.length ? "bg-red-50" : r.is_duplicate ? "bg-amber-50" : ""}`}>
                      <td className="px-4 py-2">{r.row}</td>
                      <td className="px-4 py-2">{r.data.make} {r.data.model} {r.data.registration}</td>
                      <td className="px-4 py-2">{r.data.lot_number}</td>
                      <td className="px-4 py-2">{r.data.guide_price}</td>
                      <td className="px-4 py-2">{r.data.category}</td>
                      <td className="px-4 py-2">
                        {r.importable ? <Badge tone="green">Importable</Badge> : r.is_duplicate ? <Badge tone="amber">Duplicate</Badge> : <Badge tone="red">{r.errors.join("; ")}</Badge>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardBody>
          </Card>
          <p className="text-xs text-slate-500">
            Imports use your own account&apos;s export and are labelled by source. Re-importing updates
            existing lots rather than duplicating them.
          </p>
        </>
      )}
    </div>
  );
}
