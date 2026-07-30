// Shared enum constants mirroring the API. The web app keeps richer types in apps/web/types;
// this package is the single place to share primitive unions if more workspaces are added.

export const RECOMMENDATIONS = [
  "STRONG_BUY",
  "BUY",
  "CONSIDER",
  "HIGH_RISK",
  "PASS",
  "INCOMPLETE_DATA",
] as const;
export type Recommendation = (typeof RECOMMENDATIONS)[number];

export const RISK_LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;
export type RiskLevel = (typeof RISK_LEVELS)[number];

export const ROLES = ["ADMIN", "BUYER", "VIEWER"] as const;
export type Role = (typeof ROLES)[number];
