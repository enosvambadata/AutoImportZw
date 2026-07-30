"use client";

import {
  Calculator,
  Car,
  Gauge,
  Gavel,
  ListChecks,
  LogOut,
  Settings,
  Warehouse,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "@/features/auth/auth-context";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: Gauge },
  { href: "/listings", label: "Auction listings", icon: Car },
  { href: "/shortlist", label: "Daily shortlist", icon: ListChecks },
  { href: "/evaluate", label: "Evaluate a lot", icon: Calculator },
  { href: "/appraisals", label: "Appraisals", icon: Gavel },
  { href: "/stock", label: "Stock & sales", icon: Warehouse },
  { href: "/settings", label: "Settings", icon: Settings, admin: true },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, logout, can } = useAuth();

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-slate-200 bg-white md:flex">
        <div className="flex items-center gap-2 px-5 py-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white">
            <Gavel size={18} />
          </div>
          <div className="leading-tight">
            <p className="text-sm font-semibold text-slate-900">AutoBid</p>
            <p className="text-xs text-slate-500">Intelligence</p>
          </div>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-2" aria-label="Primary">
          {NAV.filter((n) => !n.admin || can("admin")).map((item) => {
            const active = pathname.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium",
                  active ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100",
                )}
                aria-current={active ? "page" : undefined}
              >
                <Icon size={18} />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-slate-100 px-3 py-3">
          <div className="px-2 pb-2">
            <p className="truncate text-sm font-medium text-slate-800">
              {user ? `${user.first_name} ${user.last_name}` : ""}
            </p>
            <p className="text-xs text-slate-500">{user?.role}</p>
          </div>
          <button
            onClick={() => logout()}
            className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
          >
            <LogOut size={18} />
            Sign out
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 md:hidden">
          <span className="font-semibold text-brand-700">AutoBid Intelligence</span>
          <button onClick={() => logout()} className="text-sm text-slate-600">
            Sign out
          </button>
        </header>
        <main className="flex-1 p-4 md:p-6">
          <div className="mx-auto max-w-6xl">{children}</div>
        </main>
      </div>
    </div>
  );
}
