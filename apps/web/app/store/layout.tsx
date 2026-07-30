import { MessageCircle } from "lucide-react";
import { Fraunces, Inter, JetBrains_Mono } from "next/font/google";
import Link from "next/link";
import type { ReactNode } from "react";

import { WHATSAPP } from "@/lib/public-api";

const display = Fraunces({ subsets: ["latin"], variable: "--font-display", weight: ["400", "500", "600", "700"], style: ["normal", "italic"] });
const body = Inter({ subsets: ["latin"], variable: "--font-body" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", weight: ["400", "500", "600"] });

const NAV = [
  { href: "/store/cars", label: "Cars" },
  { href: "/store/vet", label: "Vet a car" },
  { href: "/store/check", label: "MOT check" },
  { href: "/store/start", label: "How it works" },
];

export default function StoreLayout({ children }: { children: ReactNode }) {
  const wa = `https://wa.me/${WHATSAPP.replace(/[^\d]/g, "")}`;
  return (
    <div className={`${display.variable} ${mono.variable} ${body.className} store-canvas flex min-h-screen flex-col text-ink`}>
      <header className="sticky top-0 z-30 border-b border-ink/10 bg-paper/85 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4">
          <Link href="/store" className="flex items-baseline gap-2">
            <span className="font-display text-xl font-semibold tracking-tight text-ink">AutoImport</span>
            <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-accent-600">/ ZW</span>
          </Link>
          <nav className="hidden items-center gap-7 sm:flex">
            {NAV.map((n) => (
              <Link key={n.href} href={n.href} className="nav-link text-sm font-medium text-ink/70 transition hover:text-ink">
                {n.label}
              </Link>
            ))}
            <a href={wa} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 rounded-full bg-ink px-4 py-2 text-sm font-semibold text-paper transition hover:bg-ink-800">
              <MessageCircle size={14} /> WhatsApp
            </a>
          </nav>
          <a href={wa} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 rounded-full bg-ink px-3 py-1.5 text-sm font-semibold text-paper sm:hidden">
            <MessageCircle size={14} /> Chat
          </a>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl grow px-5 py-10">{children}</main>

      <footer className="border-t border-ink/10">
        <div className="mx-auto max-w-6xl px-5 py-10">
          <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
            <div>
              <p className="font-display text-2xl font-semibold tracking-tight">AutoImport <span className="text-accent-600">ZW</span></p>
              <p className="mt-1 font-mono text-[11px] uppercase tracking-[0.2em] text-ink/50">UK → Zimbabwe · vetted imports</p>
            </div>
            <nav className="flex flex-wrap gap-5 text-sm text-ink/60">
              {NAV.map((n) => <Link key={n.href} href={n.href} className="hover:text-ink">{n.label}</Link>)}
            </nav>
          </div>
          <p className="mt-8 max-w-3xl border-t border-ink/10 pt-5 text-xs leading-relaxed text-ink/50">
            Every car is appraised — MOT history, condition, write-off status — before we quote. Landed
            costs are estimates; final import duty is set by ZIMRA. We buy on your approval and deposit —
            nothing is purchased without your say-so. No guarantees; a physical inspection may still be advised.
          </p>
        </div>
      </footer>
    </div>
  );
}
