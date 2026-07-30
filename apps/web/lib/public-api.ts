// Public storefront API client — no auth, hits /api/public. Separate from the authed `api` client.

const V1 = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";
const PUBLIC_BASE = V1.replace(/\/api\/v1\/?$/, "/api/public");

type Query = Record<string, string | number | boolean | undefined | null>;

async function req<T>(path: string, opts: { method?: string; body?: unknown; query?: Query } = {}): Promise<T> {
  const url = new URL(`${PUBLIC_BASE}${path}`);
  if (opts.query) {
    for (const [k, v] of Object.entries(opts.query)) {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
    }
  }
  const res = await fetch(url.toString(), {
    method: opts.method || "GET",
    headers: opts.body !== undefined ? { "Content-Type": "application/json" } : {},
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) throw new Error(data?.error?.message || res.statusText);
  return data as T;
}

export const publicApi = {
  get: <T>(path: string, query?: Query) => req<T>(path, { query }),
  post: <T>(path: string, body?: unknown) => req<T>(path, { method: "POST", body }),
};

export function formatMoney(value: string | number | null | undefined, currency = "USD"): string {
  const n = typeof value === "number" ? value : Number(value ?? 0);
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(n);
}

export const WHATSAPP = process.env.NEXT_PUBLIC_WHATSAPP || "+263000000000";
