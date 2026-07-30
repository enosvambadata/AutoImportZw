// British English + GBP formatting helpers. Values from the API are decimal strings.

const gbp = new Intl.NumberFormat("en-GB", {
  style: "currency",
  currency: "GBP",
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

const gbpPennies = new Intl.NumberFormat("en-GB", {
  style: "currency",
  currency: "GBP",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function toNumber(value: string | number | null | undefined): number {
  if (value === null || value === undefined || value === "") return NaN;
  return typeof value === "number" ? value : parseFloat(value);
}

export function formatGBP(value: string | number | null | undefined, pennies = false): string {
  const n = toNumber(value);
  if (Number.isNaN(n)) return "—";
  return (pennies ? gbpPennies : gbp).format(n);
}

export function formatPercent(value: string | number | null | undefined, digits = 1): string {
  const n = toNumber(value);
  if (Number.isNaN(n)) return "—";
  return `${(n * 100).toFixed(digits)}%`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

export function formatNumber(value: string | number | null | undefined): string {
  const n = toNumber(value);
  if (Number.isNaN(n)) return "—";
  return new Intl.NumberFormat("en-GB").format(n);
}
