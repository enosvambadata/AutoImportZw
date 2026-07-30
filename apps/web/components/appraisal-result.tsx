"use client";

import { AlertTriangle, CheckCircle2, HelpCircle } from "lucide-react";

import { Disclaimer, RecommendationBadge, RiskBadge } from "@/components/domain";
import { Badge, Card, CardBody, CardHeader } from "@/components/ui";
import { formatGBP, formatPercent, toNumber } from "@/lib/format";
import type { EvaluationResult } from "@/types";

function Tile({ label, value, hint, danger }: { label: string; value: string; hint?: string; danger?: boolean }) {
  return (
    <div className="rounded-lg border border-slate-200 p-3">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-1 text-xl font-semibold ${danger ? "text-red-600" : "text-slate-900"}`}>{value}</p>
      {hint && <p className="text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

function heat(profit: number): string {
  if (profit >= 1500) return "bg-emerald-200 text-emerald-900";
  if (profit >= 500) return "bg-emerald-100 text-emerald-800";
  if (profit >= 0) return "bg-amber-100 text-amber-900";
  if (profit >= -750) return "bg-orange-200 text-orange-900";
  return "bg-red-200 text-red-900";
}

export function AppraisalResult({ result }: { result: EvaluationResult }) {
  const { calculation: calc, risk, recommendation: rec } = result;

  return (
    <div className="space-y-4">
      {/* Recommendation */}
      <Card>
        <CardBody className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <RecommendationBadge value={rec.decision} size="lg" />
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <span>Data confidence:</span>
              <Badge tone={rec.confidence === "HIGH" ? "green" : rec.confidence === "MEDIUM" ? "amber" : "slate"}>
                {rec.confidence}
              </Badge>
              <RiskBadge value={risk.level} />
            </div>
          </div>

          <ul className="space-y-1 text-sm text-slate-700">
            {rec.reasons.map((r, i) => (
              <li key={i} className="flex gap-2"><HelpCircle size={16} className="mt-0.5 shrink-0 text-slate-400" />{r}</li>
            ))}
          </ul>

          <p className="rounded-md bg-brand-50 px-3 py-2 text-sm font-medium text-brand-800">
            Next step: {rec.next_action}
          </p>

          <div className="grid gap-3 md:grid-cols-3">
            <div>
              <p className="mb-1 text-xs font-semibold uppercase text-emerald-700">Positive factors</p>
              <ul className="space-y-1 text-sm text-slate-600">
                {rec.positive_factors.length ? rec.positive_factors.map((f, i) => (
                  <li key={i} className="flex gap-1.5"><CheckCircle2 size={14} className="mt-0.5 shrink-0 text-emerald-500" />{f}</li>
                )) : <li className="text-slate-400">None recorded</li>}
              </ul>
            </div>
            <div>
              <p className="mb-1 text-xs font-semibold uppercase text-amber-700">Warnings</p>
              <ul className="space-y-1 text-sm text-slate-600">
                {rec.warning_factors.length ? rec.warning_factors.map((f, i) => (
                  <li key={i} className="flex gap-1.5"><AlertTriangle size={14} className="mt-0.5 shrink-0 text-amber-500" />{f}</li>
                )) : <li className="text-slate-400">None recorded</li>}
              </ul>
            </div>
            <div>
              <p className="mb-1 text-xs font-semibold uppercase text-slate-600">Missing information</p>
              <ul className="space-y-1 text-sm text-slate-600">
                {rec.missing_information.length ? rec.missing_information.map((f, i) => (
                  <li key={i}>{f}</li>
                )) : <li className="text-slate-400">None</li>}
              </ul>
            </div>
          </div>
        </CardBody>
      </Card>

      {calc && (
        <>
          {/* Bid summary */}
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
            <Tile label="Safe max bid" value={formatGBP(calc.safe_max_bid)} hint="Conservative" />
            <Tile label="Absolute max bid" value={formatGBP(calc.absolute_max_bid)} hint="Hard stop" />
            <Tile label="Break-even bid" value={formatGBP(calc.break_even_bid)} hint="Zero profit" />
            <Tile label="Expected profit" value={formatGBP(calc.expected_profit)} hint={`at ${formatGBP(calc.reference_hammer)}`} danger={toNumber(calc.expected_profit) <= 0} />
            <Tile label="ROI on cash" value={formatPercent(calc.roi_on_cost)} hint={`Margin ${formatPercent(calc.margin)}`} />
            <Tile label="Worst / best" value={`${formatGBP(calc.pessimistic_profit)}`} hint={`Best ${formatGBP(calc.optimistic_profit)}`} danger={toNumber(calc.pessimistic_profit) < 0} />
          </div>

          {/* Scenario bar */}
          <Card>
            <CardHeader title="Profit scenarios" subtitle="Deterministic bands from your entered price and cost ranges" />
            <CardBody className="space-y-2">
              {[
                { k: "Pessimistic", v: calc.pessimistic_profit, tone: "bg-orange-400" },
                { k: "Expected", v: calc.expected_profit, tone: "bg-brand-500" },
                { k: "Optimistic", v: calc.optimistic_profit, tone: "bg-emerald-500" },
              ].map((s) => {
                const max = Math.max(1, toNumber(calc.optimistic_profit), 1);
                const pct = Math.max(2, (toNumber(s.v) / max) * 100);
                return (
                  <div key={s.k} className="flex items-center gap-3 text-sm">
                    <span className="w-24 text-slate-600">{s.k}</span>
                    <div className="h-4 flex-1 rounded bg-slate-100">
                      <div className={`h-4 rounded ${s.tone}`} style={{ width: `${Math.min(100, Math.abs(pct))}%` }} />
                    </div>
                    <span className="w-20 text-right font-medium">{formatGBP(s.v)}</span>
                  </div>
                );
              })}
            </CardBody>
          </Card>

          {/* Bid ladder */}
          <Card>
            <CardHeader title="Bid ladder" subtitle="Outcome at several possible hammer prices" />
            <CardBody className="overflow-x-auto p-0">
              <table className="w-full min-w-[640px] text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-left text-xs uppercase text-slate-500">
                    <th className="px-4 py-2 font-medium">Scenario</th>
                    <th className="px-4 py-2 font-medium">Hammer</th>
                    <th className="px-4 py-2 font-medium">Cash required</th>
                    <th className="px-4 py-2 font-medium">Expected profit</th>
                    <th className="px-4 py-2 font-medium">Worst case</th>
                    <th className="px-4 py-2 font-medium">ROI</th>
                  </tr>
                </thead>
                <tbody>
                  {calc.bid_ladder.map((r, i) => (
                    <tr key={i} className={`border-b border-slate-50 ${r.exceeds_absolute ? "bg-red-50" : ""}`}>
                      <td className="px-4 py-2.5 font-medium text-slate-700">
                        {r.label}
                        {r.exceeds_absolute && <Badge tone="red">Over max</Badge>}
                      </td>
                      <td className="px-4 py-2.5">{formatGBP(r.hammer)}</td>
                      <td className="px-4 py-2.5">{formatGBP(r.total_cash_required)}</td>
                      <td className={`px-4 py-2.5 font-medium ${toNumber(r.expected_profit) <= 0 ? "text-red-600" : ""}`}>{formatGBP(r.expected_profit)}</td>
                      <td className={`px-4 py-2.5 ${toNumber(r.worst_case_profit) < 0 ? "text-red-600" : ""}`}>{formatGBP(r.worst_case_profit)}</td>
                      <td className="px-4 py-2.5">{formatPercent(r.roi_on_cash)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardBody>
          </Card>

          {/* Sensitivity heatmap */}
          <Card>
            <CardHeader title="Sensitivity: expected profit" subtitle="Rows = selling price change · Columns = preparation cost change" />
            <CardBody className="overflow-x-auto">
              <table className="text-xs">
                <thead>
                  <tr>
                    <th className="p-1 text-slate-500">Price \ Cost</th>
                    {calc.sensitivity.cost_deltas.map((c) => (
                      <th key={c} className="p-1 font-medium text-slate-600">{formatPercent(c, 0)}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {calc.sensitivity.profit_matrix.map((row, ri) => (
                    <tr key={ri}>
                      <td className="p-1 font-medium text-slate-600">{formatPercent(calc.sensitivity.price_deltas[ri], 0)}</td>
                      {row.map((cell, ci) => (
                        <td key={ci} className={`p-1.5 text-center font-medium ${heat(toNumber(cell))}`}>
                          {formatGBP(cell)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardBody>
          </Card>

          {/* Risk breakdown */}
          <Card>
            <CardHeader
              title="Risk breakdown"
              subtitle={`Weighted score ${risk.weighted_total}/100`}
              action={<RiskBadge value={risk.level} />}
            />
            <CardBody className="space-y-3">
              {risk.critical_flags.length > 0 && (
                <div className="rounded-md bg-red-50 p-3 text-sm text-red-800">
                  <strong>Critical:</strong> {risk.critical_flags.join("; ")}
                </div>
              )}
              <div className="grid gap-1.5 sm:grid-cols-2 lg:grid-cols-3">
                {Object.entries(risk.scores).map(([k, v]) => (
                  <div key={k} className="flex items-center gap-2 text-xs">
                    <span className="w-28 shrink-0 capitalize text-slate-600">{k.replace(/_/g, " ")}</span>
                    <div className="h-2 flex-1 rounded bg-slate-100">
                      <div className={`h-2 rounded ${v >= 70 ? "bg-red-500" : v >= 50 ? "bg-orange-400" : v >= 25 ? "bg-amber-400" : "bg-emerald-400"}`} style={{ width: `${v}%` }} />
                    </div>
                    <span className="w-6 text-right text-slate-500">{v}</span>
                  </div>
                ))}
              </div>
              <p className="text-xs text-slate-500">Suggested risk reserve: {formatGBP(risk.suggested_risk_reserve)}</p>
            </CardBody>
          </Card>
        </>
      )}

      <Disclaimer />
    </div>
  );
}
