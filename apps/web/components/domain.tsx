import {
  AlertTriangle,
  CheckCircle2,
  CircleSlash,
  HelpCircle,
  Info,
  ShieldAlert,
  ThumbsUp,
} from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";
import type { Recommendation, RiskLevel } from "@/types";

// Never rely on colour alone: each state also carries a label and an icon.
const REC_META: Record<Recommendation, { label: string; tone: string; icon: ReactNode }> = {
  STRONG_BUY: { label: "Strong buy", tone: "bg-emerald-600 text-white", icon: <ThumbsUp size={14} /> },
  BUY: { label: "Buy", tone: "bg-emerald-100 text-emerald-800", icon: <CheckCircle2 size={14} /> },
  CONSIDER: { label: "Consider", tone: "bg-amber-100 text-amber-900", icon: <Info size={14} /> },
  HIGH_RISK: { label: "High risk", tone: "bg-orange-200 text-orange-900", icon: <ShieldAlert size={14} /> },
  PASS: { label: "Pass", tone: "bg-red-100 text-red-800", icon: <CircleSlash size={14} /> },
  INCOMPLETE_DATA: { label: "Incomplete data", tone: "bg-slate-200 text-slate-700", icon: <HelpCircle size={14} /> },
};

export function RecommendationBadge({ value, size = "sm" }: { value: Recommendation | null; size?: "sm" | "lg" }) {
  if (!value) return <span className="text-slate-400">—</span>;
  const m = REC_META[value];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full font-semibold",
        m.tone,
        size === "lg" ? "px-4 py-1.5 text-sm" : "px-2.5 py-0.5 text-xs",
      )}
    >
      {m.icon}
      {m.label}
    </span>
  );
}

const RISK_META: Record<RiskLevel, { label: string; tone: string }> = {
  LOW: { label: "Low risk", tone: "bg-emerald-100 text-emerald-800" },
  MEDIUM: { label: "Medium risk", tone: "bg-amber-100 text-amber-900" },
  HIGH: { label: "High risk", tone: "bg-orange-200 text-orange-900" },
  CRITICAL: { label: "Critical risk", tone: "bg-red-100 text-red-800" },
};

export function RiskBadge({ value }: { value: RiskLevel | null }) {
  if (!value) return <span className="text-slate-400">—</span>;
  const m = RISK_META[value];
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium", m.tone)}>
      <AlertTriangle size={12} />
      {m.label}
    </span>
  );
}

export function Disclaimer({ compact = false }: { compact?: boolean }) {
  return (
    <div className={cn("rounded-md border border-amber-200 bg-amber-50 p-3 text-amber-900", compact ? "text-xs" : "text-sm")}>
      <div className="flex gap-2">
        <Info size={compact ? 14 : 16} className="mt-0.5 shrink-0" />
        <p>
          <strong>Decision support only.</strong> Recommendations are estimates, not guarantees, and
          depend on the accuracy of entered and third-party data. A physical and mechanical inspection
          may still be required; hidden defects can materially affect profit. You remain responsible
          for all bidding and purchasing decisions.
        </p>
      </div>
    </div>
  );
}

export function DataSourceBadge({ source }: { source: string | null | undefined }) {
  if (!source) return null;
  const labels: Record<string, string> = {
    MANUAL: "Manually entered",
    MOCK_ADAPTER: "Demo data (mock)",
    CSV_IMPORT: "CSV import",
  };
  return (
    <span className="inline-flex items-center rounded bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium text-slate-500">
      {labels[source] || source}
    </span>
  );
}
