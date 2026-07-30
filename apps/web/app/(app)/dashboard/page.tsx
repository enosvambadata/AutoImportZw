"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Disclaimer, RecommendationBadge, RiskBadge } from "@/components/domain";
import { Card, CardBody, CardHeader, EmptyState, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { formatDate, formatGBP, formatPercent } from "@/lib/format";
import type { DashboardData, Recommendation, RiskLevel } from "@/types";

function StatTile({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: string }) {
  return (
    <Card className={tone}>
      <CardBody>
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
        <p className="mt-1 text-2xl font-semibold text-slate-900">{value}</p>
        {sub && <p className="mt-0.5 text-xs text-slate-500">{sub}</p>}
      </CardBody>
    </Card>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<DashboardData>("/analytics/dashboard")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <EmptyState title="Could not load the dashboard" description={error} />;
  if (!data) return <Spinner label="Loading dashboard…" />;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <p className="text-sm text-slate-500">Estimated and actual performance across your appraisals.</p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile label="Vehicles appraised" value={String(data.vehicles_appraised)} />
        <StatTile label="Strong buys & buys" value={String(data.strong_buys_and_buys)} sub={`${data.passed_vehicles} passed`} />
        <StatTile label="Avg expected profit" value={formatGBP(data.average_expected_profit)} sub="Estimated" />
        <StatTile label="Avg actual profit" value={formatGBP(data.average_actual_profit)} sub="From completed sales" />
        <StatTile label="Capital in stock" value={formatGBP(data.estimated_capital_required)} sub="Estimated (unsold)" />
        <StatTile label="Profit forecast" value={formatGBP(data.profit_forecast)} sub="Estimated pipeline" />
        <StatTile label="Avg days in stock" value={data.average_days_in_stock != null ? String(data.average_days_in_stock) : "—"} sub="Actual" />
        <StatTile label="Appraisal → purchase" value={formatPercent(data.appraisal_to_purchase_conversion)} sub="Conversion" />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader title="Recent appraisals" subtitle="Most recently created" />
          <CardBody className="p-0">
            {data.recent_appraisals.length === 0 ? (
              <div className="p-5">
                <EmptyState title="No appraisals yet" description="Create your first appraisal from a listing." />
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-left text-xs uppercase text-slate-500">
                    <th className="px-5 py-2 font-medium">Recommendation</th>
                    <th className="px-5 py-2 font-medium">Expected profit</th>
                    <th className="px-5 py-2 font-medium">Risk</th>
                    <th className="px-5 py-2 font-medium">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent_appraisals.map((a) => (
                    <tr key={a.id} className="border-b border-slate-50 hover:bg-slate-50">
                      <td className="px-5 py-2.5">
                        <Link href={`/appraisals/${a.id}`}>
                          <RecommendationBadge value={a.recommendation as Recommendation} />
                        </Link>
                      </td>
                      <td className="px-5 py-2.5 font-medium">{formatGBP(a.expected_profit)}</td>
                      <td className="px-5 py-2.5">
                        <RiskBadge value={a.risk_level as RiskLevel} />
                      </td>
                      <td className="px-5 py-2.5 text-slate-500">{formatDate(a.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Requires action" subtitle="Drafts and 'consider' outcomes" />
          <CardBody>
            {data.vehicles_requiring_action.length === 0 ? (
              <p className="text-sm text-slate-500">Nothing needs attention.</p>
            ) : (
              <ul className="space-y-2">
                {data.vehicles_requiring_action.map((v) => (
                  <li key={v.id}>
                    <Link href={`/appraisals/${v.id}`} className="flex items-center justify-between rounded-md border border-slate-100 px-3 py-2 text-sm hover:bg-slate-50">
                      <span>Appraisal #{v.id}</span>
                      <RecommendationBadge value={v.recommendation as Recommendation} />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>
      </div>

      <Disclaimer />
    </div>
  );
}
