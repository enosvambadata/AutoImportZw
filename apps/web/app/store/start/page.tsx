"use client";

import { ArrowRight, CheckCircle2, MessageCircle } from "lucide-react";
import { useState } from "react";

import { publicApi, WHATSAPP } from "@/lib/public-api";

export default function StartPage() {
  const [f, setF] = useState({ name: "", contact: "", make: "", model: "", budget_usd: "", notes: "", company: "" });
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const set = (k: keyof typeof f, v: string) => setF((p) => ({ ...p, [k]: v }));

  async function submit() {
    if (!f.name.trim() || f.contact.trim().length < 3) { setError("Please add your name and a contact."); return; }
    setBusy(true); setError(null);
    try {
      const res = await publicApi.post<{ message: string }>("/briefs", {
        name: f.name, contact: f.contact, make: f.make || null, model: f.model || null,
        budget_usd: f.budget_usd ? Number(f.budget_usd) : null, notes: f.notes || null,
        company: f.company || null,
      });
      setDone(res.message);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not send — try WhatsApp instead.");
    } finally { setBusy(false); }
  }

  const wa = `https://wa.me/${WHATSAPP.replace(/[^\d]/g, "")}?text=${encodeURIComponent("Hi, I'd like to import a car to Zimbabwe.")}`;
  const input = "w-full border border-ink/20 bg-transparent px-3 py-2.5 text-sm text-ink placeholder:text-ink/40 focus:border-ink focus:outline-none";

  if (done) {
    return (
      <div className="mx-auto max-w-xl border border-emerald-300 bg-emerald-50 p-10 text-center">
        <CheckCircle2 className="mx-auto mb-3 text-emerald-600" size={34} />
        <p className="font-display text-xl text-emerald-900">{done}</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="border-b border-ink/10 pb-6">
        <p className="overline text-accent-600">Sourcing brief · no obligation</p>
        <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight md:text-5xl">Tell us the car. We&apos;ll find it, vetted.</h1>
        <p className="mt-3 max-w-lg text-ink/60">Give us a budget and the kind of car. We source UK options, run the MOT and damage checks, and send you a full landed cost to Zimbabwe — before you commit a cent.</p>
      </div>

      <div className="mt-8 grid gap-8 md:grid-cols-5">
        <div className="space-y-3 md:col-span-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <input value={f.name} onChange={(e) => set("name", e.target.value)} placeholder="Your name" className={input} />
            <input value={f.contact} onChange={(e) => set("contact", e.target.value)} placeholder="WhatsApp / phone / email" className={input} />
            <input value={f.make} onChange={(e) => set("make", e.target.value)} placeholder="Make (e.g. Toyota)" className={input} />
            <input value={f.model} onChange={(e) => set("model", e.target.value)} placeholder="Model (e.g. Hilux)" className={input} />
          </div>
          <input value={f.budget_usd} onChange={(e) => set("budget_usd", e.target.value.replace(/[^\d]/g, ""))} placeholder="Budget in USD (delivered)" className={input} />
          <textarea value={f.notes} onChange={(e) => set("notes", e.target.value)} rows={3} placeholder="Anything else — body type, year, must-haves…" className={input} />
          <input type="text" tabIndex={-1} autoComplete="off" aria-hidden="true" className="hidden" value={f.company} onChange={(e) => set("company", e.target.value)} />
          {error && <p className="text-xs text-red-600">{error}</p>}
          <button onClick={submit} disabled={busy} className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-ink px-4 py-3 text-sm font-semibold text-paper transition hover:bg-ink-800 disabled:opacity-60">
            {busy ? "Sending…" : "Send my brief"} <ArrowRight size={15} />
          </button>
          <a href={wa} target="_blank" rel="noopener noreferrer" className="inline-flex w-full items-center justify-center gap-2 rounded-full border border-emerald-500 px-4 py-3 text-sm font-semibold text-emerald-700 transition hover:bg-emerald-50">
            <MessageCircle size={15} /> Or message us on WhatsApp
          </a>
        </div>

        <aside className="md:col-span-2">
          <div className="border border-ink/12 bg-white/50 p-5">
            <p className="overline text-ink/40">What happens next</p>
            <ol className="mt-3 space-y-3 text-sm text-ink/70">
              <li className="flex gap-3"><span className="font-mono text-accent-600">01</span> We shortlist vetted UK cars to your brief.</li>
              <li className="flex gap-3"><span className="font-mono text-accent-600">02</span> You get MOT history, condition and a landed-cost quote.</li>
              <li className="flex gap-3"><span className="font-mono text-accent-600">03</span> Approve one, pay a deposit, and we buy &amp; ship it.</li>
            </ol>
          </div>
        </aside>
      </div>
    </div>
  );
}
