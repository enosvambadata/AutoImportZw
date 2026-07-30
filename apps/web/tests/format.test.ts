import { describe, expect, it } from "vitest";

import { formatGBP, formatPercent, toNumber } from "@/lib/format";
import { auctionStatus, remainingRoom } from "@/features/appraisals/auction-status";

describe("format helpers", () => {
  it("formats GBP without pennies by default", () => {
    expect(formatGBP("1200")).toBe("£1,200");
    expect(formatGBP("1200.55", true)).toBe("£1,200.55");
  });

  it("returns an em dash for missing values", () => {
    expect(formatGBP(null)).toBe("—");
    expect(formatGBP("")).toBe("—");
    expect(formatPercent(undefined)).toBe("—");
  });

  it("formats ratios as percentages", () => {
    expect(formatPercent("0.15")).toBe("15.0%");
    expect(formatPercent("0.153", 0)).toBe("15%");
  });

  it("parses decimal strings", () => {
    expect(toNumber("42.5")).toBe(42.5);
    expect(Number.isNaN(toNumber(null))).toBe(true);
  });
});

describe("auction status", () => {
  it("is ok at or below the safe maximum", () => {
    expect(auctionStatus(5000, 5500, 6400)).toBe("ok");
    expect(auctionStatus(5500, 5500, 6400)).toBe("ok");
  });

  it("is caution above safe but not above absolute", () => {
    expect(auctionStatus(6000, 5500, 6400)).toBe("caution");
  });

  it("is STOP above the absolute maximum", () => {
    expect(auctionStatus(6500, 5500, 6400)).toBe("stop");
  });

  it("computes remaining room (negative when over)", () => {
    expect(remainingRoom(6000, 6400)).toBe(400);
    expect(remainingRoom(6800, 6400)).toBe(-400);
  });
});
