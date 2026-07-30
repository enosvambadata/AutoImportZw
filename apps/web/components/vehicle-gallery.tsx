"use client";

import { ChevronLeft, ChevronRight, ImageIcon, Play, Rotate3d, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

function mediaUrl(params: Record<string, string | number>): string {
  const q = new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)]));
  return `${API}/media/car.svg?${q.toString()}`;
}

/** Real provider photos when present, else labelled demo studio frames. */
export function galleryImages(seed: string, label: string, images?: string[]): string[] {
  if (images && images.length) return images;
  return [0, 1, 2, 3, 4, 5].map((shot) => mediaUrl({ seed, label, shot }));
}

export function spinFrames(seed: string, label: string, spin?: string[], frames = 24): string[] {
  if (spin && spin.length) return spin;
  return Array.from({ length: frames }, (_, i) =>
    mediaUrl({ seed, label, angle: Math.round((i * 360) / frames) }),
  );
}

// ---- 360° spin viewer (drag to rotate, or auto-spin) ----
function Spin360({ frames }: { frames: string[] }) {
  const [idx, setIdx] = useState(0);
  const [auto, setAuto] = useState(false);
  const drag = useRef<{ x: number; idx: number } | null>(null);

  useEffect(() => {
    // Preload frames so the spin is smooth.
    frames.forEach((f) => {
      const img = new Image();
      img.src = f;
    });
  }, [frames]);

  useEffect(() => {
    if (!auto) return;
    const t = setInterval(() => setIdx((i) => (i + 1) % frames.length), 80);
    return () => clearInterval(t);
  }, [auto, frames.length]);

  const move = (clientX: number) => {
    if (!drag.current) return;
    const delta = clientX - drag.current.x;
    const step = Math.round(delta / 8);
    setIdx((((drag.current.idx + step) % frames.length) + frames.length) % frames.length);
  };

  return (
    <div className="select-none">
      <div
        className="relative cursor-ew-resize overflow-hidden rounded-lg bg-slate-900"
        onPointerDown={(e) => { drag.current = { x: e.clientX, idx }; setAuto(false); (e.target as HTMLElement).setPointerCapture(e.pointerId); }}
        onPointerMove={(e) => move(e.clientX)}
        onPointerUp={() => (drag.current = null)}
        role="img"
        aria-label="360 degree view — drag to rotate"
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={frames[idx]} alt="360 view" className="w-full" draggable={false} />
        <div className="pointer-events-none absolute left-1/2 top-3 -translate-x-1/2 rounded-full bg-black/40 px-3 py-1 text-xs font-medium text-white">
          <span className="inline-flex items-center gap-1"><Rotate3d size={13} /> Drag to rotate</span>
        </div>
      </div>
      <div className="mt-2 flex items-center gap-3">
        <button onClick={() => setAuto((a) => !a)} className="inline-flex items-center gap-1.5 rounded-md bg-slate-100 px-3 py-1.5 text-sm hover:bg-slate-200">
          <Play size={14} /> {auto ? "Stop" : "Auto-spin"}
        </button>
        <input type="range" min={0} max={frames.length - 1} value={idx} onChange={(e) => { setAuto(false); setIdx(Number(e.target.value)); }} className="flex-1" aria-label="Rotate" />
      </div>
    </div>
  );
}

// ---- Full gallery (photos + 360 tabs) ----
function Gallery({ seed, label, images, spin }: { seed: string; label: string; images?: string[]; spin?: string[] }) {
  const imgs = galleryImages(seed, label, images);
  const frames = spinFrames(seed, label, spin);
  const [i, setI] = useState(0);
  const [tab, setTab] = useState<"photos" | "spin">("photos");
  const demo = !(images && images.length);

  const next = useCallback(() => setI((x) => (x + 1) % imgs.length), [imgs.length]);
  const prev = useCallback(() => setI((x) => (x - 1 + imgs.length) % imgs.length), [imgs.length]);

  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (tab === "photos") { if (e.key === "ArrowRight") next(); if (e.key === "ArrowLeft") prev(); } };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [tab, next, prev]);

  return (
    <div>
      <div className="mb-3 flex items-center gap-2">
        <button onClick={() => setTab("photos")} className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm ${tab === "photos" ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600"}`}>
          <ImageIcon size={14} /> Photos
        </button>
        <button onClick={() => setTab("spin")} className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm ${tab === "spin" ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600"}`}>
          <Rotate3d size={14} /> 360° view
        </button>
        {demo && <span className="ml-auto rounded bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-900">Demo imagery</span>}
      </div>

      {tab === "photos" ? (
        <div>
          <div className="relative overflow-hidden rounded-lg bg-slate-900">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={imgs[i]} alt={`${label} photo ${i + 1}`} className="w-full" />
            <button onClick={prev} aria-label="Previous" className="absolute left-2 top-1/2 -translate-y-1/2 rounded-full bg-black/40 p-2 text-white hover:bg-black/60"><ChevronLeft size={20} /></button>
            <button onClick={next} aria-label="Next" className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full bg-black/40 p-2 text-white hover:bg-black/60"><ChevronRight size={20} /></button>
            <div className="absolute bottom-2 right-3 rounded-full bg-black/40 px-2 py-0.5 text-xs text-white">{i + 1} / {imgs.length}</div>
          </div>
          <div className="mt-2 flex gap-2 overflow-x-auto pb-1">
            {imgs.map((src, k) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img key={k} src={src} alt="" onClick={() => setI(k)} className={`h-16 w-24 shrink-0 cursor-pointer rounded-md object-cover ring-2 ${k === i ? "ring-brand-500" : "ring-transparent"}`} />
            ))}
          </div>
        </div>
      ) : (
        <Spin360 frames={frames} />
      )}
    </div>
  );
}

// ---- Thumbnail that opens a lightbox — the reusable piece for lists ----
export function VehicleMedia({ seed, label, images, spin, className }: {
  seed: string; label: string; images?: string[]; spin?: string[]; className?: string;
}) {
  const [open, setOpen] = useState(false);
  const thumb = galleryImages(seed, label, images)[0];

  return (
    <>
      <button onClick={() => setOpen(true)} className={`group relative block overflow-hidden rounded-lg bg-slate-900 ${className ?? ""}`} aria-label={`View photos of ${label}`}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={thumb} alt={label} className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105" />
        <span className="absolute bottom-1.5 right-1.5 inline-flex items-center gap-1 rounded-full bg-black/50 px-2 py-0.5 text-[11px] font-medium text-white">
          <Rotate3d size={11} /> 360°
        </span>
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" role="dialog" aria-modal="true" onClick={() => setOpen(false)}>
          <div className="w-full max-w-3xl rounded-xl bg-white p-4 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-base font-semibold text-slate-900">{label}</h3>
              <button onClick={() => setOpen(false)} aria-label="Close" className="rounded-md p-1 text-slate-500 hover:bg-slate-100"><X size={18} /></button>
            </div>
            <Gallery seed={seed} label={label} images={images} spin={spin} />
          </div>
        </div>
      )}
    </>
  );
}
