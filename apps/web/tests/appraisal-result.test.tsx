import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AppraisalResult } from "@/components/appraisal-result";
import { RecommendationBadge } from "@/components/domain";
import type { EvaluationResult } from "@/types";

const RESULT: EvaluationResult = {
  calculation: {
    safe_max_bid: "5520.00",
    absolute_max_bid: "6391.00",
    break_even_bid: "7200.00",
    reference_hammer: "5000.00",
    expected_profit: "1559.80",
    pessimistic_profit: "900.00",
    optimistic_profit: "2200.00",
    total_cash_invested: "6500.00",
    roi_on_cost: "0.24",
    roi_on_hammer: "0.31",
    margin: "0.17",
    meets_target: true,
    meets_roi: true,
    fee_at_reference: "400.00",
    bid_ladder: [
      { label: "Safe maximum", hammer: "5520.00", fee: "530.00", total_cash_required: "6900.00", expected_profit: "1200.00", worst_case_profit: "500.00", roi_on_cash: "0.17", margin: "0.13", exceeds_absolute: false },
      { label: "Above absolute (do not exceed)", hammer: "6891.00", fee: "600.00", total_cash_required: "8000.00", expected_profit: "200.00", worst_case_profit: "-400.00", roi_on_cash: "0.02", margin: "0.02", exceeds_absolute: true },
    ],
    sensitivity: {
      price_deltas: ["-0.15", "0", "0.10"],
      cost_deltas: ["-0.10", "0", "0.50"],
      profit_matrix: [["-200", "100", "-900"], ["1000", "1559.80", "700"], ["2200", "2500", "1800"]],
      days_axis: [0, 30, 60],
      days_profit: ["1559.80", "1559.80", "1559.80"],
      discount_axis: ["0", "500"],
      discount_profit: ["1700", "1200"],
    },
  },
  risk: {
    scores: { mechanical: 10, history: 5, mot: 0 },
    weighted_total: 12,
    level: "LOW",
    explanations: ["Mechanical risk scored 10/100"],
    warning_flags: [],
    critical_flags: [],
    suggested_risk_reserve: "160",
    policy_blocks: [],
  },
  recommendation: {
    decision: "STRONG_BUY",
    reasons: ["Expected profit beats target by 25%."],
    positive_factors: ["ROI clears the threshold"],
    warning_factors: [],
    missing_information: [],
    next_action: "Bid with confidence up to your safe maximum.",
    confidence: "HIGH",
  },
};

describe("AppraisalResult", () => {
  it("renders the recommendation, bids and next action", () => {
    render(<AppraisalResult result={RESULT} />);
    expect(screen.getByText("Strong buy")).toBeInTheDocument();
    expect(screen.getByText("Safe max bid")).toBeInTheDocument();
    expect(screen.getAllByText(/£5,520/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Bid with confidence/)).toBeInTheDocument();
  });

  it("flags bid-ladder rungs above the absolute maximum", () => {
    render(<AppraisalResult result={RESULT} />);
    expect(screen.getByText("Over max")).toBeInTheDocument();
  });

  it("always shows the decision-support disclaimer", () => {
    render(<AppraisalResult result={RESULT} />);
    expect(screen.getByText(/Decision support only/)).toBeInTheDocument();
  });
});

describe("RecommendationBadge", () => {
  it("shows a label (not colour alone) for each decision", () => {
    render(<RecommendationBadge value="PASS" />);
    expect(screen.getByText("Pass")).toBeInTheDocument();
  });
});
