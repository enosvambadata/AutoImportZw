"use client";

import { ArrowRight, ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { CarCard } from "@/components/store/car-card";
import { formatMoney, publicApi } from "@/lib/public-api";
import type { PublicCarSummary, PublicStats } from "@/types/store";

const STEPS = [
  { n: "01", title: "We source & vet", body: "Hand-picked from UK auctions, dealers, Auto Trader, Facebook Marketplace and retired company fleets — cars and trucks — and checked for MOT history, write-off status and damage before you ever commit." },
  { n: "02", title: "You see the landed cost", body: "One delivered price in USD — car, fees, shipping and duty, itemised. No surprises, no hidden margins." },
  { n: "03", title: "You approve & deposit", body: "Happy with the car and the number? A deposit reserves it. Nothing is bought without your say-so." },
  { n: "04", title: "We buy & ship", body: "We secure it — an auction bid or a private purchase — export it, and ship to your port, then inland to your door in Zimbabwe." },
];

const VETTING = [
  ["Official DVSA", "MOT history on every car"],
  ["Write-off status", "Category checked & disclosed"],
  ["Right-hand drive", "UK stock, no conversion"],
  ["Landed in USD", "Full cost before you commit"],
];

const TICKER = ["MOT verified", "Write-off checked", "Right-hand drive", "Landed cost in USD", "Buy on approval", "No hidden margins"];

export default function StoreHome() {
  const [stats, setStats] = useState<PublicStats | null>(null);
  const [cars, setCars] = useState<PublicCarSummary[]>([]);
  const [delivered, setDelivered] = useState<PublicCarSummary[]>([]);

  useEffect(() => {
    publicApi.get<PublicStats>("/stats").then(setStats).catch(() => {});
    publicApi.get<PublicCarSummary[]>("/cars").then(setCars).catch(() => {});
    publicApi.get<PublicCarSummary[]>("/delivered").then(setDelivered).catch(() => {});
  }, []);

  const featured = cars[0];

  return (
    <div className="space-y-24">
      {/* Hero */}
      <section className="store-hero relative overflow-hidden rounded-2xl text-paper">
        <div className="store-grid absolute inset-0 opacity-70" />
        <p className="ghost-metric pointer-events-none absolute -right-4 -top-10 select-none text-[13rem] md:text-[20rem]">ZW</p>
        <div className="relative grid gap-10 p-8 md:grid-cols-5 md:p-14">
          <div className="md:col-span-3">
            <p className="reveal overline text-accent-300" style={{ animationDelay: "0ms" }}>UK → Zimbabwe · vetted imports</p>
            <h1 className="reveal mt-6 font-display font-semibold tracking-[-0.02em]" style={{ animationDelay: "80ms", fontSize: "clamp(2.9rem, 8vw, 6.4rem)", lineHeight: 0.98 }}>
              Import a car you can<br /><span className="italic text-accent-300">actually trust.</span>
            </h1>
            <p className="reveal mt-7 max-w-lg text-lg leading-relaxed text-paper/70" style={{ animationDelay: "160ms" }}>
              Right-hand-drive UK cars and trucks — from auctions, marketplaces and retired company
              fleets — appraised before you buy: MOT history, honest condition, and a full landed cost
              in USD. You approve and deposit; we source, buy and ship.
            </p>
            <div className="reveal mt-9 flex flex-wrap gap-3" style={{ animationDelay: "240ms" }}>
              <Link href="/store/cars" className="group inline-flex items-center gap-2 rounded-full bg-paper px-6 py-3 font-semibold text-ink transition hover:bg-white">
                Browse cars <ArrowRight size={16} className="transition group-hover:translate-x-1" />
              </Link>
              <Link href="/store/start" className="inline-flex items-center gap-2 rounded-full border border-paper/25 px-6 py-3 font-semibold text-paper transition hover:bg-paper/10">
                Tell us what you want
              </Link>
            </div>
            {stats && (
              <div className="reveal mt-11 flex flex-wrap gap-x-10 gap-y-3 font-mono text-sm text-paper/55" style={{ animationDelay: "320ms" }}>
                <span><span className="text-2xl text-paper">{stats.delivered}</span> delivered</span>
                <span className="self-center text-paper/20">/</span>
                <span><span className="text-2xl text-paper">{stats.available}</span> available now</span>
                <span className="self-center text-paper/20">/</span>
                <span><span className="text-2xl text-paper">{stats.destinations.length}</span> destination{stats.destinations.length === 1 ? "" : "s"}</span>
              </div>
            )}
          </div>

          {/* Dossier panel */}
          <div className="reveal md:col-span-2" style={{ animationDelay: "300ms" }}>
            <div className="rounded-xl border border-paper/15 bg-paper/[0.04] p-5 backdrop-blur">
              <div className="flex items-center justify-between">
                <p className="overline text-paper/40">Sample dossier</p>
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent-400" />
              </div>
              {featured ? (
                <>
                  <p className="mt-3 font-display text-2xl leading-tight">{featured.model_year} {featured.make} {featured.model}</p>
                  <dl className="mt-4 space-y-2 font-mono text-sm">
                    <Row k="Mileage" v={featured.mileage ? `${new Intl.NumberFormat("en-GB").format(featured.mileage)} mi` : "—"} />
                    <Row k="Fuel" v={featured.fuel_type || "—"} />
                    <Row k="MOT" v="verified" accent />
                    <div className="my-2 border-t border-paper/10" />
                    <Row k="Landed" v={formatMoney(featured.landed_total, featured.currency)} big />
                  </dl>
                  <Link href={`/store/car/${featured.slug}`} className="mt-4 inline-flex items-center gap-1 font-mono text-xs uppercase tracking-wide text-accent-300 hover:text-accent-200">
                    View full dossier <ArrowUpRight size={13} />
                  </Link>
                </>
              ) : (
                <p className="mt-3 font-mono text-sm leading-relaxed text-paper/50">
                  make · model · mileage<br />MOT history · write-off status<br />landed cost, itemised, in USD
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Trust ticker */}
        <div className="relative overflow-hidden border-t border-paper/10 py-3">
          <div className="marquee-track font-mono text-xs uppercase tracking-[0.2em] text-paper/45">
            {[...TICKER, ...TICKER].map((t, i) => (
              <span key={i} className="mx-6 inline-flex items-center gap-6">{t}<span className="text-accent-400">✦</span></span>
            ))}
          </div>
        </div>
      </section>

      {/* Vetting strip */}
      <section className="grid grid-cols-1 divide-y divide-ink/10 border-y border-ink/10 sm:grid-cols-2 sm:divide-x lg:grid-cols-4 lg:divide-y-0">
        {VETTING.map(([label, desc], i) => (
          <div key={label} className="px-5 py-6 first:pl-0 lg:px-6">
            <p className="font-mono text-xs text-accent-600">0{i + 1}</p>
            <p className="mt-2 font-display text-lg">{label}</p>
            <p className="mt-1 text-sm text-ink/55">{desc}</p>
          </div>
        ))}
      </section>

      {/* Process */}
      <section>
        <div className="flex items-baseline justify-between border-b border-ink/10 pb-4">
          <h2 className="font-display text-3xl font-semibold tracking-tight md:text-4xl">The process</h2>
          <p className="hidden font-mono text-xs uppercase tracking-widest text-ink/40 sm:block">You&apos;re in control at every step</p>
        </div>
        <div>
          {STEPS.map((s) => (
            <div key={s.n} className="group grid gap-2 border-b border-ink/10 py-8 transition-colors hover:bg-ink/[0.02] md:grid-cols-12 md:gap-6">
              <p className="font-display text-4xl text-accent-500 transition-transform group-hover:translate-x-1 md:col-span-1">{s.n}</p>
              <p className="font-display text-xl md:col-span-3">{s.title}</p>
              <p className="max-w-xl text-ink/60 md:col-span-8">{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Statement band — a rest beat with one big claim */}
      <section className="store-hero relative overflow-hidden rounded-2xl px-8 py-16 text-paper md:px-14 md:py-20">
        <div className="store-grid absolute inset-0 opacity-50" />
        <div className="relative grid items-center gap-8 md:grid-cols-2">
          <p className="font-display text-3xl font-semibold leading-tight tracking-tight md:text-[2.75rem]">
            The car&apos;s history is on the table <span className="italic text-accent-300">before</span> the money is.
          </p>
          <p className="max-w-md justify-self-start text-paper/70 md:justify-self-end">
            Most imports are bought blind. We hand you the official MOT record, the write-off status and an
            itemised landed cost first — then you decide. That is the whole difference.
          </p>
        </div>
      </section>

      {/* Available now */}
      <section>
        <div className="mb-6 flex items-end justify-between border-b border-ink/10 pb-4">
          <h2 className="font-display text-3xl font-semibold tracking-tight md:text-4xl">Available now</h2>
          <Link href="/store/cars" className="nav-link inline-flex items-center gap-1 font-mono text-xs uppercase tracking-widest text-ink/60 hover:text-ink">All cars <ArrowRight size={13} /></Link>
        </div>
        {cars.length === 0 ? (
          <div className="border border-dashed border-ink/20 p-16 text-center">
            <p className="font-display text-2xl">No cars published yet</p>
            <p className="mt-1 text-sm text-ink/55">Tell us what you&apos;re after and we&apos;ll source it for you.</p>
            <Link href="/store/start" className="mt-6 inline-flex items-center gap-2 rounded-full bg-ink px-5 py-2.5 text-sm font-semibold text-paper hover:bg-ink-800">Tell us what you want <ArrowRight size={15} /></Link>
          </div>
        ) : (
          <div className="grid gap-5 md:grid-cols-3">
            {cars.slice(0, 3).map((c) => <CarCard key={c.slug} car={c} />)}
          </div>
        )}
      </section>

      {/* Recently delivered — proof */}
      {delivered.length > 0 && (
        <section>
          <div className="mb-6 flex items-end justify-between border-b border-ink/10 pb-4">
            <div>
              <p className="overline text-accent-600">Proof · real jobs</p>
              <h2 className="mt-2 font-display text-3xl font-semibold tracking-tight md:text-4xl">Recently delivered</h2>
            </div>
            <p className="hidden font-mono text-xs uppercase tracking-widest text-ink/40 sm:block">Sourced · vetted · shipped</p>
          </div>
          <div className="grid gap-5 md:grid-cols-3">
            {delivered.slice(0, 3).map((c) => <CarCard key={c.slug} car={c} />)}
          </div>
        </section>
      )}

      {/* CTA */}
      <section className="relative overflow-hidden rounded-2xl border border-ink/15 bg-white/50 px-8 py-16 text-center md:px-14">
        <p className="ghost-metric pointer-events-none absolute inset-x-0 -bottom-8 select-none text-center text-[9rem] md:text-[14rem]" style={{ WebkitTextStroke: "1px rgba(18,16,12,0.06)" }}>SOURCE</p>
        <div className="relative">
          <p className="overline text-accent-600">No obligation</p>
          <h2 className="mx-auto mt-4 max-w-2xl font-display text-4xl font-semibold tracking-tight md:text-5xl">Can&apos;t see the car you want?</h2>
          <p className="mx-auto mt-3 max-w-lg text-ink/60">Give us your budget and the kind of car — we&apos;ll source vetted UK options with a full landed cost to your door.</p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link href="/store/start" className="group inline-flex items-center gap-2 rounded-full bg-ink px-7 py-3.5 font-semibold text-paper transition hover:bg-ink-800">
              Tell us what you want <ArrowRight size={16} className="transition group-hover:translate-x-1" />
            </Link>
            <Link href="/store/vet" className="inline-flex items-center gap-2 rounded-full border border-ink/20 px-7 py-3.5 font-semibold text-ink transition hover:bg-ink/5">
              Found one? We&apos;ll vet it
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}

function Row({ k, v, big, accent }: { k: string; v: string; big?: boolean; accent?: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-paper/45">{k}</dt>
      <dd className={`${big ? "text-lg text-accent-300" : accent ? "text-accent-300" : "text-paper/90"}`}>{v}</dd>
    </div>
  );
}
