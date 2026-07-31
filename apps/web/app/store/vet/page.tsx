"use client";

import { ArrowRight, CheckCircle2, MessageCircle, ShieldCheck } from "lucide-react";
import { useState } from "react";

import { publicApi, WHATSAPP } from "@/lib/public-api";

export default function VetPage() {
  const [f, setF] = useState({ name: "", contact: "", source_url: "", listing_text: "", company: "" });
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const set = (k: keyof typeof f, v: string) => setF((p) => ({ ...p, [k]: v }));

  async function submit() {
    if (!f.name.trim() || f.contact.trim().length < 3) { setError("Please add your name and a contact."); return; }
    if (!f.source_url.trim() && !f.listing_text.trim()) { setError("Paste the car's link or its listing details."); return; }
    setBusy(true); setError(null);
    try {
      const res = await publicApi.post<{ message: string }>("/vet-request", {
        name: f.name, contact: f.contact,
        source_url: f.source_url || null, listing_text: f.listing_text || null,
        company: f.company || null,
      });
      setDone(res.message);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not send — try WhatsApp instead.");
    } finally { setBusy(false); }
  }

  const wa = `https://wa.me/${WHATSAPP.replace(/[^\d]/g, "")}?text=${encodeURIComponent("Hi, can you vet a car I found?")}`;
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
        <p className="overline text-accent-600">Found a car? · we&apos;ll vet it</p>
        <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight md:text-5xl">Send us any car or truck. We&apos;ll tell you the truth.</h1>
        <p className="mt-3 max-w-xl text-ink/60">
          Seen one anywhere — an auction, Auto Trader, Facebook Marketplace, a dealer or a private seller?
          Paste the link (or the listing details) and we&apos;ll pull the MOT history, check the write-off
          status and condition, and send you a full landed cost to Zimbabwe — before you commit a cent.
        </p>
      </div>

      <div className="mt-8 grid gap-8 md:grid-cols-5">
        <div className="space-y-3 md:col-span-3">
          <input value={f.source_url} onChange={(e) => set("source_url", e.target.value)} placeholder="Paste the link (auction, Auto Trader, Facebook Marketplace, dealer…)" className={input} />
          <div className="flex items-center gap-3 text-xs uppercase tracking-widest text-ink/35">
            <span className="h-px flex-1 bg-ink/10" /> or paste the details <span className="h-px flex-1 bg-ink/10" />
          </div>
          <textarea value={f.listing_text} onChange={(e) => set("listing_text", e.target.value)} rows={4} placeholder="Make, model, year, mileage, reg, damage — whatever the listing shows" className={input} />
          <div className="grid gap-3 sm:grid-cols-2">
            <input value={f.name} onChange={(e) => set("name", e.target.value)} placeholder="Your name" className={input} />
            <input value={f.contact} onChange={(e) => set("contact", e.target.value)} placeholder="WhatsApp / phone / email" className={input} />
          </div>
          <input type="text" tabIndex={-1} autoComplete="off" aria-hidden="true" className="hidden" value={f.company} onChange={(e) => set("company", e.target.value)} />
          {error && <p className="text-xs text-red-600">{error}</p>}
          <button onClick={submit} disabled={busy} className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-ink px-4 py-3 text-sm font-semibold text-paper transition hover:bg-ink-800 disabled:opacity-60">
            {busy ? "Sending…" : "Vet this car for me"} <ArrowRight size={15} />
          </button>
          <a href={wa} target="_blank" rel="noopener noreferrer" className="inline-flex w-full items-center justify-center gap-2 rounded-full border border-emerald-500 px-4 py-3 text-sm font-semibold text-emerald-700 transition hover:bg-emerald-50">
            <MessageCircle size={15} /> Or send the link on WhatsApp
          </a>
        </div>

        <aside className="md:col-span-2">
          <div className="border border-ink/12 bg-white/50 p-5">
            <p className="inline-flex items-center gap-2 font-display text-lg"><ShieldCheck size={18} className="text-emerald-600" /> What we check</p>
            <ul className="mt-3 space-y-2 text-sm text-ink/70">
              <li className="flex gap-3"><span className="font-mono text-accent-600">01</span> Official DVSA MOT history &amp; mileage</li>
              <li className="flex gap-3"><span className="font-mono text-accent-600">02</span> Write-off category &amp; recorded damage</li>
              <li className="flex gap-3"><span className="font-mono text-accent-600">03</span> A full landed cost to your door, in USD</li>
            </ul>
            <p className="mt-4 border-t border-ink/10 pt-3 text-xs text-ink/45">No obligation. We only source cars we&apos;d be happy to put our name to.</p>
          </div>
        </aside>
      </div>
    </div>
  );
}
