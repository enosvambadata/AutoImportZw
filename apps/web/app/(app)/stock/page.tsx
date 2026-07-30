"use client";

import { useEffect, useState } from "react";

import { Badge, Button, Card, CardBody, CardHeader, EmptyState, Field, Input, Spinner } from "@/components/ui";
import { useAuth } from "@/features/auth/auth-context";
import { api } from "@/lib/api";
import { formatDate, formatGBP } from "@/lib/format";

interface Purchase {
  id: number;
  appraisal_id: number;
  actual_hammer_price: string;
  stock_number: string | null;
  preparation_status: string;
  purchase_date: string;
  total_preparation_cost: string | null;
  total_invested: string | null;
  preparation_costs: Array<{ id: number; description: string; category: string; actual_amount: string }>;
}

interface Sale {
  id: number;
  purchase_id: number;
  final_selling_price: string;
  gross_profit: string | null;
  net_contribution: string | null;
  days_in_stock: number | null;
}

export default function StockPage() {
  const { can } = useAuth();
  const [purchases, setPurchases] = useState<Purchase[] | null>(null);
  const [sales, setSales] = useState<Sale[]>([]);
  const [active, setActive] = useState<number | null>(null);
  const [prep, setPrep] = useState({ description: "", category: "SERVICE", actual_amount: "" });
  const [sale, setSale] = useState({ final_selling_price: "", warranty_cost: "0", advertising_cost: "0", finance_commission: "0" });
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const [p, s] = await Promise.all([api.get<Purchase[]>("/purchases"), api.get<Sale[]>("/sales")]);
    setPurchases(p);
    setSales(s);
  }
  useEffect(() => { load().catch((e) => setError(e.message)); }, []);

  const soldIds = new Set(sales.map((s) => s.purchase_id));

  async function addPrep(purchaseId: number) {
    if (!prep.description) return;
    await api.post(`/purchases/${purchaseId}/preparation-costs`, prep);
    setPrep({ description: "", category: "SERVICE", actual_amount: "" });
    load();
  }
  async function completeSale(purchaseId: number) {
    setError(null);
    try {
      await api.post("/sales", {
        purchase_id: purchaseId,
        final_selling_price: sale.final_selling_price || "0",
        sale_date: new Date().toISOString().slice(0, 10),
        warranty_cost: sale.warranty_cost || "0",
        advertising_cost: sale.advertising_cost || "0",
        finance_commission: sale.finance_commission || "0",
      });
      setActive(null);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sale failed");
    }
  }

  if (!purchases) return <Spinner label="Loading stock…" />;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Stock &amp; sales</h1>
        <p className="text-sm text-slate-500">Purchased vehicles, actual preparation costs and completed sales.</p>
      </div>

      {error && <p className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      {purchases.length === 0 ? (
        <EmptyState title="No purchases yet" description="Mark an appraisal as purchased to add it to stock." />
      ) : (
        purchases.map((p) => {
          const relatedSale = sales.find((s) => s.purchase_id === p.id);
          return (
            <Card key={p.id}>
              <CardHeader
                title={`Stock ${p.stock_number ?? "#" + p.id}`}
                subtitle={`Purchased ${formatDate(p.purchase_date)} · hammer ${formatGBP(p.actual_hammer_price)}`}
                action={<Badge tone={soldIds.has(p.id) ? "green" : "blue"}>{soldIds.has(p.id) ? "Sold" : p.preparation_status}</Badge>}
              />
              <CardBody className="space-y-3">
                <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
                  <div><p className="text-xs uppercase text-slate-400">Total invested</p><p className="font-semibold">{formatGBP(p.total_invested)}</p></div>
                  <div><p className="text-xs uppercase text-slate-400">Prep costs (actual)</p><p className="font-semibold">{formatGBP(p.total_preparation_cost)}</p></div>
                  {relatedSale && <div><p className="text-xs uppercase text-slate-400">Actual net profit</p><p className="font-semibold text-emerald-700">{formatGBP(relatedSale.net_contribution)}</p></div>}
                  {relatedSale && <div><p className="text-xs uppercase text-slate-400">Days in stock</p><p className="font-semibold">{relatedSale.days_in_stock}</p></div>}
                </div>

                {p.preparation_costs.length > 0 && (
                  <ul className="text-sm text-slate-600">
                    {p.preparation_costs.map((c) => (
                      <li key={c.id} className="flex justify-between border-b border-slate-50 py-1">
                        <span>{c.description} <Badge>{c.category}</Badge></span>
                        <span>{formatGBP(c.actual_amount)}</span>
                      </li>
                    ))}
                  </ul>
                )}

                {can("write") && !soldIds.has(p.id) && (
                  <div className="space-y-3 border-t border-slate-100 pt-3">
                    <div className="grid gap-2 md:grid-cols-4">
                      <Input placeholder="Prep description" value={active === p.id ? prep.description : ""} onFocus={() => setActive(p.id)} onChange={(e) => { setActive(p.id); setPrep({ ...prep, description: e.target.value }); }} />
                      <select className="rounded-md border border-slate-300 px-2 text-sm" value={prep.category} onChange={(e) => setPrep({ ...prep, category: e.target.value })}>
                        {["SERVICE", "MECHANICAL", "BODYWORK", "TYRES", "MOT", "VALETING", "OTHER"].map((c) => <option key={c}>{c}</option>)}
                      </select>
                      <Input placeholder="Amount £" value={active === p.id ? prep.actual_amount : ""} onChange={(e) => setPrep({ ...prep, actual_amount: e.target.value })} />
                      <Button variant="secondary" onClick={() => addPrep(p.id)}>Add prep cost</Button>
                    </div>

                    {active === p.id ? (
                      <div className="rounded-md bg-slate-50 p-3">
                        <p className="mb-2 text-sm font-medium text-slate-700">Complete sale</p>
                        <div className="grid gap-2 md:grid-cols-4">
                          <Field label="Selling price £"><Input value={sale.final_selling_price} onChange={(e) => setSale({ ...sale, final_selling_price: e.target.value })} /></Field>
                          <Field label="Warranty £"><Input value={sale.warranty_cost} onChange={(e) => setSale({ ...sale, warranty_cost: e.target.value })} /></Field>
                          <Field label="Advertising £"><Input value={sale.advertising_cost} onChange={(e) => setSale({ ...sale, advertising_cost: e.target.value })} /></Field>
                          <Field label="Finance commission £"><Input value={sale.finance_commission} onChange={(e) => setSale({ ...sale, finance_commission: e.target.value })} /></Field>
                        </div>
                        <div className="mt-2"><Button onClick={() => completeSale(p.id)}>Record sale</Button></div>
                      </div>
                    ) : null}
                  </div>
                )}
              </CardBody>
            </Card>
          );
        })
      )}
    </div>
  );
}
