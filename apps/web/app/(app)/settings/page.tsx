"use client";

import { useEffect, useState } from "react";

import { AuctionHouseGeo } from "@/components/auction-house-geo";
import { ConnectorsCard } from "@/components/connectors-card";
import { Badge, Button, Card, CardBody, CardHeader, Field, Input, Spinner } from "@/components/ui";
import { useAuth } from "@/features/auth/auth-context";
import { api } from "@/lib/api";
import { formatGBP, formatPercent } from "@/lib/format";
import type { AuctionHouse, User } from "@/types";

interface Dealership {
  id: number;
  name: string;
  default_target_profit: string;
  default_risk_reserve: string;
  mandatory_min_risk_reserve: string;
  default_min_roi: string;
  vat_rate: string;
  max_acceptable_pessimistic_loss: string;
  allow_category_n: boolean;
  allow_category_s: boolean;
}

export default function SettingsPage() {
  const { can } = useAuth();
  const [dealership, setDealership] = useState<Dealership | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [houses, setHouses] = useState<AuctionHouse[]>([]);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<Dealership>("/dealership").then(setDealership).catch((e) => setError(e.message));
    api.get<AuctionHouse[]>("/auction-houses").then(setHouses).catch(() => {});
    if (can("admin")) api.get<User[]>("/users").then(setUsers).catch(() => {});
  }, [can]);

  async function saveDealership() {
    if (!dealership) return;
    setError(null);
    try {
      await api.patch("/dealership", {
        default_target_profit: dealership.default_target_profit,
        default_risk_reserve: dealership.default_risk_reserve,
        mandatory_min_risk_reserve: dealership.mandatory_min_risk_reserve,
        default_min_roi: dealership.default_min_roi,
        vat_rate: dealership.vat_rate,
        max_acceptable_pessimistic_loss: dealership.max_acceptable_pessimistic_loss,
        allow_category_n: dealership.allow_category_n,
        allow_category_s: dealership.allow_category_s,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  }

  if (!dealership) return <Spinner label="Loading settings…" />;
  const upd = (k: keyof Dealership, v: string | boolean) => setDealership({ ...dealership, [k]: v });
  const readOnly = !can("admin");

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Settings</h1>
        <p className="text-sm text-slate-500">
          {readOnly ? "Read-only — administrator access required to change these." : "Dealership defaults and purchasing policy."}
        </p>
      </div>
      {error && <p className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      <Card>
        <CardHeader title="Calculation defaults" subtitle={dealership.name} />
        <CardBody className="grid gap-3 md:grid-cols-3">
          <Field label="Default target profit (£)"><Input disabled={readOnly} value={dealership.default_target_profit} onChange={(e) => upd("default_target_profit", e.target.value)} /></Field>
          <Field label="Default risk reserve (£)"><Input disabled={readOnly} value={dealership.default_risk_reserve} onChange={(e) => upd("default_risk_reserve", e.target.value)} /></Field>
          <Field label="Mandatory min reserve (£)"><Input disabled={readOnly} value={dealership.mandatory_min_risk_reserve} onChange={(e) => upd("mandatory_min_risk_reserve", e.target.value)} /></Field>
          <Field label="Minimum ROI (0-1)"><Input disabled={readOnly} value={dealership.default_min_roi} onChange={(e) => upd("default_min_roi", e.target.value)} /></Field>
          <Field label="VAT rate (0-1)"><Input disabled={readOnly} value={dealership.vat_rate} onChange={(e) => upd("vat_rate", e.target.value)} /></Field>
          <Field label="Max acceptable pessimistic loss (£)"><Input disabled={readOnly} value={dealership.max_acceptable_pessimistic_loss} onChange={(e) => upd("max_acceptable_pessimistic_loss", e.target.value)} /></Field>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" disabled={readOnly} checked={dealership.allow_category_n} onChange={(e) => upd("allow_category_n", e.target.checked)} /> Allow Category N vehicles</label>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" disabled={readOnly} checked={dealership.allow_category_s} onChange={(e) => upd("allow_category_s", e.target.checked)} /> Allow Category S vehicles</label>
          {!readOnly && (
            <div className="md:col-span-3">
              <Button onClick={saveDealership}>Save defaults</Button>
              {saved && <span className="ml-3 text-sm text-emerald-600">Saved.</span>}
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Auction houses & fee bands" />
        <CardBody className="space-y-3">
          {houses.map((h) => (
            <div key={h.id} className="rounded-md border border-slate-100 p-3">
              <div className="flex items-center justify-between">
                <p className="font-medium text-slate-800">{h.name}</p>
                <Badge>{h.fee_calc_type}</Badge>
              </div>
              <AuctionHouseGeo id={h.id} postcode={h.postcode} editable={can("admin")} />
              <ul className="mt-1 text-sm text-slate-600">
                {h.fee_bands.map((b) => (
                  <li key={b.id}>
                    {b.label ?? "Band"}: {formatPercent(b.percentage)} + {formatGBP(b.fixed_fee)}
                    {b.minimum_fee && ` · min ${formatGBP(b.minimum_fee)}`}
                    {b.maximum_fee && ` · max ${formatGBP(b.maximum_fee)}`}
                    {b.vat_applicable && " · +VAT"}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </CardBody>
      </Card>

      {can("admin") && <ConnectorsCard />}

      {can("admin") && (
        <Card>
          <CardHeader title="Users" subtitle="Role-based access is enforced by the API." />
          <CardBody className="p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-left text-xs uppercase text-slate-500">
                  <th className="px-5 py-2 font-medium">Name</th><th className="px-5 py-2 font-medium">Email</th>
                  <th className="px-5 py-2 font-medium">Role</th><th className="px-5 py-2 font-medium">Active</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-b border-slate-50">
                    <td className="px-5 py-2">{u.first_name} {u.last_name}</td>
                    <td className="px-5 py-2 text-slate-600">{u.email}</td>
                    <td className="px-5 py-2"><Badge tone={u.role === "ADMIN" ? "purple" : u.role === "BUYER" ? "blue" : "slate"}>{u.role}</Badge></td>
                    <td className="px-5 py-2">{u.active ? "Yes" : "No"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardBody>
        </Card>
      )}
    </div>
  );
}
