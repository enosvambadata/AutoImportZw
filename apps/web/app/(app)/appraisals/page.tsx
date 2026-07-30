"use client";

import { Plus } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { RecommendationBadge, RiskBadge } from "@/components/domain";
import { Button, Card, CardBody, EmptyState, Spinner } from "@/components/ui";
import { useAuth } from "@/features/auth/auth-context";
import { api } from "@/lib/api";
import { formatDate, formatGBP } from "@/lib/format";
import type { Appraisal, Page, Recommendation } from "@/types";

const REC_FILTERS: Array<Recommendation | ""> = ["", "STRONG_BUY", "BUY", "CONSIDER", "HIGH_RISK", "PASS"];

export default function AppraisalsPage() {
  const { can } = useAuth();
  const [data, setData] = useState<Page<Appraisal> | null>(null);
  const [rec, setRec] = useState<Recommendation | "">("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .get<Page<Appraisal>>("/appraisals", { recommendation: rec || undefined, page_size: 50 })
      .then(setData)
      .finally(() => setLoading(false));
  }, [rec]);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Appraisals</h1>
          <p className="text-sm text-slate-500">Every completed and draft appraisal.</p>
        </div>
        {can("write") && (
          <Link href="/appraisals/new">
            <Button><Plus size={16} /> New appraisal</Button>
          </Link>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        {REC_FILTERS.map((r) => (
          <button
            key={r || "all"}
            onClick={() => setRec(r)}
            className={`rounded-full px-3 py-1 text-sm ${rec === r ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600"}`}
          >
            {r ? r.replace("_", " ") : "All"}
          </button>
        ))}
      </div>

      <Card>
        <CardBody className="p-0">
          {loading ? (
            <div className="p-5"><Spinner /></div>
          ) : !data || data.items.length === 0 ? (
            <div className="p-5"><EmptyState title="No appraisals" description="Create one from a listing or manually." /></div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-left text-xs uppercase text-slate-500">
                  <th className="px-5 py-2 font-medium">#</th>
                  <th className="px-5 py-2 font-medium">Recommendation</th>
                  <th className="px-5 py-2 font-medium">Safe / Absolute</th>
                  <th className="px-5 py-2 font-medium">Expected profit</th>
                  <th className="px-5 py-2 font-medium">Risk</th>
                  <th className="px-5 py-2 font-medium">Status</th>
                  <th className="px-5 py-2 font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((a) => (
                  <tr key={a.id} className="cursor-pointer border-b border-slate-50 hover:bg-slate-50">
                    <td className="px-5 py-2.5"><Link href={`/appraisals/${a.id}`} className="font-medium text-brand-700">#{a.id}</Link></td>
                    <td className="px-5 py-2.5"><RecommendationBadge value={a.recommendation} /></td>
                    <td className="px-5 py-2.5 text-slate-600">{formatGBP(a.safe_max_bid)} / {formatGBP(a.absolute_max_bid)}</td>
                    <td className="px-5 py-2.5 font-medium">{formatGBP(a.expected_profit)}</td>
                    <td className="px-5 py-2.5"><RiskBadge value={a.risk_level} /></td>
                    <td className="px-5 py-2.5 text-slate-500">{a.status}</td>
                    <td className="px-5 py-2.5 text-slate-500">{formatDate(a.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
