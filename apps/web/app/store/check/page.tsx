"use client";

import { ArrowRight } from "lucide-react";
import { useState } from "react";

import { formatDate } from "@/lib/format";
import { publicApi } from "@/lib/public-api";
import type { PublicMot } from "@/types/store";

export default function CheckPage() {
  const [reg, setReg] = useState("");
  const [mot, setMot] = useState<PublicMot | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function check() {
    if (reg.trim().length < 2) return;
    setBusy(true); setError(null); setMot(null);
    try {
      setMot(await publicApi.get<PublicMot>("/check", { reg: reg.trim() }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "No record found");
    } finally { setBusy(false); }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div className="border-b border-ink/10 pb-6">
        <p className="overline text-accent-600">Free tool · official DVSA data</p>
        <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight md:text-5xl">Read any UK car&apos;s MOT history</h1>
        <p className="mt-3 max-w-lg text-ink/60">The same check we run on every car before we import it. Enter a registration — see every test, every failure, every recorded mileage.</p>
      </div>

      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          value={reg}
          onChange={(e) => setReg(e.target.value.toUpperCase())}
          onKeyDown={(e) => e.key === "Enter" && check()}
          placeholder="MF65 KHM"
          className="grow border border-ink/25 bg-transparent px-4 py-3 font-mono text-xl uppercase tracking-widest text-ink placeholder:text-ink/30 focus:border-ink focus:outline-none"
        />
        <button onClick={check} disabled={busy || reg.trim().length < 2} className="inline-flex items-center justify-center gap-2 rounded-full bg-ink px-7 py-3 font-semibold text-paper transition hover:bg-ink-800 disabled:opacity-50">
          {busy ? "Reading…" : "Read history"} <ArrowRight size={16} />
        </button>
      </div>
      {error && <p className="border border-accent-500/40 bg-accent-50 px-4 py-3 text-sm text-accent-700">{error}</p>}

      {mot && (
        <div>
          <div className="flex flex-wrap gap-2 border-y border-ink/10 py-4 font-mono text-xs uppercase tracking-wide">
            <span className="border border-emerald-300 bg-emerald-50 px-2.5 py-1 text-emerald-700">Valid to {mot.expiry ? formatDate(mot.expiry) : "—"}</span>
            <span className="border border-ink/15 px-2.5 py-1 text-ink/70">{mot.pass_count} pass / {mot.fail_count} fail</span>
            <span className="border border-ink/15 px-2.5 py-1 text-ink/70">{mot.advisory_count} advisories</span>
            <span className={`px-2.5 py-1 ${mot.dangerous_defect_count ? "border border-red-300 bg-red-50 text-red-700" : "border border-ink/15 text-ink/70"}`}>{mot.dangerous_defect_count} dangerous</span>
          </div>
          {mot.tests.length > 0 && (
            <div className="mt-5 overflow-x-auto">
              <table className="w-full font-mono text-sm">
                <thead>
                  <tr className="border-b border-ink/15 text-left text-[10px] uppercase tracking-widest text-ink/40">
                    <th className="py-2 pr-3">Date</th><th className="py-2 pr-3">Result</th><th className="py-2 pr-3">Odometer</th><th className="py-2 pr-3">Expiry</th>
                  </tr>
                </thead>
                <tbody>
                  {mot.tests.map((t, i) => (
                    <tr key={i} className="border-b border-ink/8">
                      <td className="py-2 pr-3">{t.date ? formatDate(t.date) : "—"}</td>
                      <td className="py-2 pr-3"><span className={t.result === "PASSED" ? "text-emerald-700" : "text-red-600"}>{t.result}</span></td>
                      <td className="py-2 pr-3 tabular-nums">{t.odometer != null ? `${new Intl.NumberFormat("en-GB").format(t.odometer)} ${t.unit ?? ""}`.trim() : "—"}</td>
                      <td className="py-2 pr-3">{t.expiry ? formatDate(t.expiry) : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
