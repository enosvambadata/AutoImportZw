"use client";

import { ArrowLeft, CheckCircle2, PlayCircle } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { formatDate } from "@/lib/format";
import { formatMoney, publicApi, WHATSAPP } from "@/lib/public-api";
import type { PublicCarDetail } from "@/types/store";

function embedUrl(url: string): string | null {
  const yt = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]+)/);
  if (yt) return `https://www.youtube.com/embed/${yt[1]}`;
  const vimeo = url.match(/vimeo\.com\/(\d+)/);
  if (vimeo) return `https://player.vimeo.com/video/${vimeo[1]}`;
  return null;
}

const LANDED_ROWS: Array<[keyof PublicCarDetail["landed"], string]> = [
  ["vehicle_price", "Vehicle"],
  ["auction_fees", "Auction fees"],
  ["uk_transport", "UK transport"],
  ["ocean_freight", "Ocean freight (to Walvis Bay)"],
  ["inland_transport", "Inland transport"],
  ["estimated_repairs", "Repairs (est.)"],
  ["service_fee", "Service fee"],
];

// ZIMRA import taxes, shown as their own group.
const DUTY_ROWS: Array<[keyof PublicCarDetail["landed"], string]> = [
  ["import_duty", "Customs duty"],
  ["import_surtax", "Surtax"],
  ["import_vat", "VAT"],
];

export default function CarDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const [car, setCar] = useState<PublicCarDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    publicApi.get<PublicCarDetail>(`/cars/${slug}`).then(setCar).catch((e) => setError(e.message));
  }, [slug]);

  if (error) return <p className="border border-red-300 bg-red-50 p-4 text-sm text-red-700">{error}</p>;
  if (!car) return <p className="font-mono text-sm text-ink/50">Loading…</p>;

  const embed = car.video_url ? embedUrl(car.video_url) : null;
  const cur = car.currency;
  const specs = [
    car.derivative, car.mileage ? `${new Intl.NumberFormat("en-GB").format(car.mileage)} mi` : null,
    car.fuel_type, car.transmission, car.colour,
  ].filter(Boolean) as string[];

  return (
    <div className="space-y-8">
      <Link href="/store/cars" className="inline-flex items-center gap-1.5 font-mono text-xs uppercase tracking-wide text-ink/50 hover:text-ink">
        <ArrowLeft size={14} /> All cars
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-ink/10 pb-6">
        <div>
          <p className="overline text-accent-600">Dossier · {car.slug}</p>
          <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight md:text-5xl">{car.model_year} {car.make} {car.model}</h1>
          <div className="mt-3 flex flex-wrap gap-1.5">{specs.map((s) => <span key={s} className="spec-chip">{s}</span>)}</div>
        </div>
        {car.status === "RESERVED" && <span className="bg-accent-500 px-3 py-1 font-mono text-xs font-bold uppercase tracking-wide text-white">Reserved</span>}
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="space-y-8 lg:col-span-2">
          {/* Gallery */}
          {car.images.length > 0 && <Gallery images={car.images} alt={`${car.make} ${car.model}`} />}

          {/* Video */}
          <div className="overflow-hidden rounded-xl border border-ink/12">
            {embed ? (
              <div className="aspect-video"><iframe src={embed} title="Walkaround" className="h-full w-full" allowFullScreen /></div>
            ) : car.video_url ? (
              <a href={car.video_url} target="_blank" rel="noopener noreferrer" className="flex aspect-video items-center justify-center gap-2 bg-ink font-medium text-paper hover:bg-ink-800">
                <PlayCircle size={22} /> Watch the walkaround
              </a>
            ) : (
              <div className="flex aspect-video items-center justify-center gap-2 bg-[linear-gradient(135deg,#efeadf,#e5ded0)] font-mono text-sm uppercase tracking-wide text-ink/40">
                <PlayCircle size={18} /> Video on request
              </div>
            )}
          </div>

          {/* Condition */}
          {(car.blurb || car.notes) && (
            <section>
              <p className="overline text-accent-600">Condition — honestly</p>
              <div className="mt-3 border-t border-ink/10 pt-4">
                {car.blurb && <p className="text-lg leading-relaxed text-ink/80">{car.blurb}</p>}
                {car.notes && <p className="mt-3 leading-relaxed text-ink/55">{car.notes}</p>}
                {car.category_marker && <p className="mt-4 inline-flex border border-accent-500/40 bg-accent-50 px-3 py-1 font-mono text-xs uppercase tracking-wide text-accent-700">Insurance category · {car.category_marker}</p>}
              </div>
            </section>
          )}

          {/* MOT record */}
          {car.mot && (
            <section>
              <div className="flex items-baseline justify-between">
                <p className="overline text-accent-600">MOT record · official DVSA</p>
                <p className="font-mono text-xs text-ink/50">valid to {car.mot.expiry ? formatDate(car.mot.expiry) : "—"}</p>
              </div>
              <div className="mt-3 flex flex-wrap gap-2 border-t border-ink/10 pt-4 font-mono text-xs">
                <span className="border border-ink/15 px-2 py-1 uppercase tracking-wide text-ink/70">{car.mot.pass_count} pass / {car.mot.fail_count} fail</span>
                <span className="border border-ink/15 px-2 py-1 uppercase tracking-wide text-ink/70">{car.mot.advisory_count} advisories</span>
                <span className={`px-2 py-1 uppercase tracking-wide ${car.mot.dangerous_defect_count ? "border border-red-300 bg-red-50 text-red-700" : "border border-ink/15 text-ink/70"}`}>{car.mot.dangerous_defect_count} dangerous</span>
              </div>
              {car.mot.tests.length > 0 && (
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full font-mono text-sm">
                    <thead>
                      <tr className="border-b border-ink/15 text-left text-[10px] uppercase tracking-widest text-ink/40">
                        <th className="py-2 pr-3">Date</th><th className="py-2 pr-3">Result</th><th className="py-2 pr-3">Odometer</th><th className="py-2 pr-3">Expiry</th>
                      </tr>
                    </thead>
                    <tbody>
                      {car.mot.tests.map((t, i) => (
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
            </section>
          )}
        </div>

        {/* Sidebar: landed cost + enquiry */}
        <div className="space-y-5 lg:sticky lg:top-24 lg:self-start">
          <section className="overflow-hidden rounded-xl border border-ink/15">
            <div className="store-hero p-6 text-paper">
              <p className="overline text-paper/45">Landed · {car.landed.dest_city || car.landed.dest_country}</p>
              <p className="mt-2 font-mono text-4xl font-semibold tabular-nums">{formatMoney(car.landed.total, cur)}</p>
              <p className="mt-1 font-mono text-[11px] uppercase tracking-wide text-paper/45">estimate · {car.landed.dest_port ? `via ${car.landed.dest_port}` : "port TBC"}</p>
            </div>
            <dl className="space-y-2 bg-white/50 p-5 font-mono text-sm">
              {LANDED_ROWS.map(([k, label]) => (
                <div key={k} className="flex justify-between">
                  <dt className="text-ink/50">{label}</dt>
                  <dd className="tabular-nums">{formatMoney(car.landed[k], cur)}</dd>
                </div>
              ))}
              <p className="pt-1 text-[10px] uppercase tracking-widest text-ink/35">Zimbabwe import taxes (ZIMRA)</p>
              {DUTY_ROWS.map(([k, label]) => (
                <div key={k} className="flex justify-between">
                  <dt className="text-ink/50">{label}</dt>
                  <dd className="tabular-nums">{formatMoney(car.landed[k], cur)}</dd>
                </div>
              ))}
              <div className="mt-1 flex justify-between border-t border-ink/12 pt-3 text-base">
                <dt className="font-semibold">Total delivered</dt>
                <dd className="font-semibold tabular-nums text-accent-700">{formatMoney(car.landed.total, cur)}</dd>
              </div>
            </dl>
            <p className="border-t border-ink/10 bg-white/50 px-5 py-3 text-xs text-ink/45">
              Import taxes are calculated on the CIF value per ZIMRA (customs duty by vehicle type, 35%
              surtax on passenger cars over 5 yrs, then VAT). An estimate — the final assessment is
              ZIMRA&apos;s; every figure is confirmed before you pay.
            </p>
          </section>

          <EnquiryForm slug={car.slug} headline={`${car.model_year} ${car.make} ${car.model}`} />
        </div>
      </div>
    </div>
  );
}

function Gallery({ images, alt }: { images: string[]; alt: string }) {
  const [active, setActive] = useState(0);
  const [ok, setOk] = useState<Record<number, boolean>>({});
  const visible = images.filter((_, i) => ok[i] !== false);
  // If the currently-selected image failed, fall back to the first surviving one.
  const src = images[active];
  return (
    <div>
      <div className="relative overflow-hidden rounded-xl border border-ink/12 bg-[linear-gradient(135deg,#efeadf,#e5ded0)]">
        <div className="aspect-[4/3] w-full">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img key={src} src={src} alt={alt} className="h-full w-full object-cover"
               onError={() => setOk((p) => ({ ...p, [active]: false }))} />
        </div>
        {visible.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center font-mono text-xs uppercase tracking-wide text-ink/40">Photos loading — add files to /public{images[0]?.replace(/[^/]+$/, "")}</div>
        )}
      </div>
      {images.length > 1 && (
        <div className="mt-3 grid grid-cols-6 gap-2">
          {images.map((im, i) => (
            <button key={i} onClick={() => setActive(i)} className={`aspect-[4/3] overflow-hidden rounded border ${active === i ? "border-ink" : "border-ink/12"}`}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={im} alt="" loading="lazy" className="h-full w-full object-cover"
                   onError={(e) => { e.currentTarget.parentElement!.style.display = "none"; }} />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function EnquiryForm({ slug, headline }: { slug: string; headline: string }) {
  const [name, setName] = useState("");
  const [contact, setContact] = useState("");
  const [message, setMessage] = useState("");
  const [company, setCompany] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!name.trim() || contact.trim().length < 3) { setError("Please add your name and a contact."); return; }
    setBusy(true); setError(null);
    try {
      const res = await publicApi.post<{ message: string }>("/enquiries", { slug, name, contact, message, company: company || null });
      setDone(res.message);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not send — try WhatsApp instead.");
    } finally { setBusy(false); }
  }

  const wa = `https://wa.me/${WHATSAPP.replace(/[^\d]/g, "")}?text=${encodeURIComponent(`Hi, I'm interested in the ${headline} (${slug}).`)}`;
  const input = "w-full border border-ink/20 bg-transparent px-3 py-2.5 text-sm text-ink placeholder:text-ink/40 focus:border-ink focus:outline-none";

  if (done) {
    return (
      <section className="border border-emerald-300 bg-emerald-50 p-5 text-center">
        <CheckCircle2 className="mx-auto mb-1 text-emerald-600" size={24} />
        <p className="text-sm text-emerald-900">{done}</p>
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-ink/12 bg-white/50 p-5">
      <p className="font-display text-lg">Reserve or enquire</p>
      <p className="mb-3 text-xs text-ink/50">We&apos;ll talk you through the deposit and next steps.</p>
      <div className="space-y-2">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" className={input} />
        <input value={contact} onChange={(e) => setContact(e.target.value)} placeholder="WhatsApp / phone / email" className={input} />
        <textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={3} placeholder="Anything you'd like to ask?" className={input} />
        <input type="text" tabIndex={-1} autoComplete="off" aria-hidden="true" className="hidden" value={company} onChange={(e) => setCompany(e.target.value)} />
        {error && <p className="text-xs text-red-600">{error}</p>}
        <button onClick={submit} disabled={busy} className="w-full rounded-full bg-ink px-4 py-2.5 text-sm font-semibold text-paper transition hover:bg-ink-800 disabled:opacity-60">
          {busy ? "Sending…" : "Send enquiry"}
        </button>
        <a href={wa} target="_blank" rel="noopener noreferrer" className="block rounded-full border border-emerald-500 px-4 py-2.5 text-center text-sm font-semibold text-emerald-700 transition hover:bg-emerald-50">
          Message on WhatsApp
        </a>
      </div>
    </section>
  );
}
