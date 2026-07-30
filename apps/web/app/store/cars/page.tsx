"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { CarCard } from "@/components/store/car-card";
import { publicApi } from "@/lib/public-api";
import type { PublicCarSummary } from "@/types/store";

export default function CarsPage() {
  const [cars, setCars] = useState<PublicCarSummary[] | null>(null);
  const [all, setAll] = useState<PublicCarSummary[]>([]);
  const [make, setMake] = useState("");
  const [maxPrice, setMaxPrice] = useState("");

  function load() {
    publicApi
      .get<PublicCarSummary[]>("/cars", { make: make || undefined, max_price: maxPrice || undefined })
      .then(setCars)
      .catch(() => setCars([]));
  }
  useEffect(() => {
    publicApi.get<PublicCarSummary[]>("/cars").then((c) => { setAll(c); setCars(c); }).catch(() => setCars([]));
  }, []);

  const makes = Array.from(new Set(all.map((c) => c.make))).sort();
  const field = "border border-ink/20 bg-transparent px-3 py-2 font-mono text-sm text-ink focus:border-ink focus:outline-none";
  const chip = (active: boolean) => `border px-3 py-1.5 font-mono text-xs uppercase tracking-wide transition ${active ? "border-ink bg-ink text-paper" : "border-ink/20 text-ink/60 hover:border-ink/50"}`;

  return (
    <div className="space-y-8">
      <div className="border-b border-ink/10 pb-5">
        <p className="overline text-accent-600">Vetted picks</p>
        <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight">Cars we&apos;d put our name to</h1>
        <p className="mt-2 max-w-xl text-ink/55">A hand-picked selection — each one already appraised for MOT history, write-off status and condition, with a full landed price to Zimbabwe. Not a live auction feed; these are cars we&apos;ve vetted.</p>
      </div>

      <div className="flex flex-col items-start justify-between gap-3 border border-ink/12 bg-white/50 p-4 sm:flex-row sm:items-center">
        <p className="text-sm text-ink/70"><span className="font-display text-base">Seen one elsewhere?</span> Send us any Copart / IAA / SYNETIQ link and we&apos;ll vet it &amp; quote it.</p>
        <Link href="/store/vet" className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-ink px-4 py-2 text-sm font-semibold text-paper hover:bg-ink-800">Vet a car <span aria-hidden>→</span></Link>
      </div>

      <div className="space-y-4">
        {makes.length > 1 && (
          <div className="flex flex-wrap items-center gap-2">
            <span className="overline mr-1 text-ink/40">Make</span>
            <button onClick={() => { setMake(""); }} className={chip(!make)}>All</button>
            {makes.map((m) => <button key={m} onClick={() => setMake(m)} className={chip(make === m)}>{m}</button>)}
          </div>
        )}
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-sm">
            <span className="overline mb-1.5 block text-ink/40">Max landed (USD)</span>
            <input value={maxPrice} onChange={(e) => setMaxPrice(e.target.value.replace(/[^\d]/g, ""))} placeholder="15000" className={`w-36 ${field}`} />
          </label>
          <button onClick={load} className="rounded-full bg-ink px-5 py-2 text-sm font-semibold text-paper transition hover:bg-ink-800">Apply</button>
          {(make || maxPrice) && (
            <button onClick={() => { setMake(""); setMaxPrice(""); setCars(all); }} className="font-mono text-xs uppercase tracking-wide text-ink/50 hover:text-ink">Clear</button>
          )}
        </div>
      </div>

      {cars === null ? (
        <p className="font-mono text-sm text-ink/50">Loading…</p>
      ) : cars.length === 0 ? (
        <div className="border border-dashed border-ink/20 p-14 text-center">
          <p className="font-display text-xl">No cars match your filter</p>
          <p className="mt-1 text-sm text-ink/55">Tell us what you&apos;re after on the <Link href="/store/start" className="underline decoration-accent-500 underline-offset-2">Get started</Link> page.</p>
        </div>
      ) : (
        <div className="grid gap-5 md:grid-cols-3">
          {cars.map((c) => <CarCard key={c.slug} car={c} />)}
        </div>
      )}
    </div>
  );
}
