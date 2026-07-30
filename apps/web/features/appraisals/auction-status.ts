// Pure helper for Auction Mode: decide the bid status band. Unit-tested.

export type AuctionStatus = "ok" | "caution" | "stop";

export function auctionStatus(bid: number, safeMax: number, absoluteMax: number): AuctionStatus {
  if (bid > absoluteMax) return "stop";
  if (bid > safeMax) return "caution";
  return "ok";
}

export function remainingRoom(bid: number, absoluteMax: number): number {
  return absoluteMax - bid;
}
