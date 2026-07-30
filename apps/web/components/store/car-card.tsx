"use client";

import { ArrowUpRight } from "lucide-react";
import Link from "next/link";

import { formatMoney } from "@/lib/public-api";
import type { PublicCarSummary } from "@/types/store";

export function CarCard({ car }: { car: PublicCarSummary }) {
  const specs = [
    car.mileage ? `${new Intl.NumberFormat("en-GB").format(car.mileage)} mi` : null,
    car.fuel_type, car.transmission,
  ].filter(Boolean) as string[];

  return (
    <Link href={`/store/car/${car.slug}`} className="group flex flex-col overflow-hidden rounded-xl border border-ink/12 bg-white/60 transition hover:-translate-y-0.5 hover:border-ink/25 hover:shadow-lift">
      <div className="relative flex aspect-[16/10] items-center justify-center overflow-hidden border-b border-ink/10 bg-[linear-gradient(135deg,#efeadf,#e5ded0)]">
        <span className="font-display text-2xl italic text-ink/25 transition-transform duration-500 group-hover:scale-110">{car.make}</span>
        {car.thumb && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={car.thumb} alt={`${car.make} ${car.model}`} loading="lazy"
               onError={(e) => { e.currentTarget.style.display = "none"; }}
               className="absolute inset-0 h-full w-full object-cover transition-transform duration-500 group-hover:scale-105" />
        )}
        {car.has_video && <span className="absolute left-3 top-3 z-10 border border-ink/15 bg-paper/80 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-ink/70">▶ Video</span>}
        {car.status === "RESERVED" && <span className="absolute right-3 top-3 z-10 bg-accent-500 px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wide text-white">Reserved</span>}
        {car.status === "DELIVERED" && <span className="absolute right-3 top-3 z-10 bg-emerald-600 px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wide text-white">Delivered</span>}
      </div>
      <div className="flex grow flex-col p-5">
        <p className="font-display text-lg leading-snug">{car.model_year} {car.make} {car.model}</p>
        {car.derivative && <p className="text-sm text-ink/50">{car.derivative}</p>}
        <div className="mt-3 flex flex-wrap gap-1.5">
          {specs.map((s) => <span key={s} className="spec-chip">{s}</span>)}
        </div>
        <div className="mt-5 flex items-end justify-between border-t border-ink/10 pt-4">
          <div>
            <p className="font-mono text-xl font-semibold tabular-nums text-ink">{formatMoney(car.landed_total, car.currency)}</p>
            <p className="font-mono text-[11px] uppercase tracking-wide text-ink/40">landed · {car.dest_city || car.dest_country}</p>
          </div>
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-ink/15 text-ink transition group-hover:bg-ink group-hover:text-paper"><ArrowUpRight size={16} /></span>
        </div>
      </div>
    </Link>
  );
}
