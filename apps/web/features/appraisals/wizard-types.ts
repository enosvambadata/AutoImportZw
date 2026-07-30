// Wizard form state and helpers shared with the preview/save calls.

export interface WizardState {
  // identification
  registration: string;
  make: string;
  model: string;
  derivative: string;
  model_year: string;
  mileage: string;
  number_of_keys: string;
  category_marker: string;
  notes: string;
  imported: boolean;
  // auction
  auction_house_id: string;
  lot_number: string;
  guide_price: string;
  current_bid: string;
  vat_status: string;
  condition_grade: string;
  runner_status: string;
  // history / risk signals
  mot_fail_count: string;
  dangerous_defect_count: string;
  mileage_discrepancy: boolean;
  finance_marker: boolean;
  stolen_marker: boolean;
  missing_service_history: boolean;
  // valuation
  expected_retail_price: string;
  conservative_retail_price: string;
  optimistic_retail_price: string;
  expected_negotiated_discount: string;
  pricing_confidence: string;
  // costs
  costs: Array<{ name: string; category: string; estimated_amount: string; minimum_amount: string; maximum_amount: string }>;
  // profit
  target_profit: string;
  desired_roi: string;
  risk_reserve: string;
  estimated_days_to_sell: string;
}

export const DEFAULT_STATE: WizardState = {
  registration: "",
  make: "",
  model: "",
  derivative: "",
  model_year: "",
  mileage: "",
  number_of_keys: "2",
  category_marker: "",
  notes: "",
  imported: false,
  auction_house_id: "",
  lot_number: "",
  guide_price: "",
  current_bid: "",
  vat_status: "MARGIN",
  condition_grade: "2",
  runner_status: "RUNNER",
  mot_fail_count: "0",
  dangerous_defect_count: "0",
  mileage_discrepancy: false,
  finance_marker: false,
  stolen_marker: false,
  missing_service_history: false,
  expected_retail_price: "",
  conservative_retail_price: "",
  optimistic_retail_price: "",
  expected_negotiated_discount: "150",
  pricing_confidence: "MEDIUM",
  costs: [{ name: "Preparation service", category: "SERVICE", estimated_amount: "250", minimum_amount: "200", maximum_amount: "350" }],
  target_profit: "1200",
  desired_roi: "0.15",
  risk_reserve: "300",
  estimated_days_to_sell: "45",
};

const num = (v: string) => (v.trim() === "" ? null : v);

export function toPreviewRequest(s: WizardState) {
  return {
    expected_retail_price: num(s.expected_retail_price),
    conservative_retail_price: num(s.conservative_retail_price),
    optimistic_retail_price: num(s.optimistic_retail_price),
    expected_negotiated_discount: s.expected_negotiated_discount || "0",
    target_profit: s.target_profit || "0",
    risk_reserve: s.risk_reserve || "0",
    desired_roi: s.desired_roi || "0.15",
    estimated_days_to_sell: Number(s.estimated_days_to_sell) || 45,
    current_bid: num(s.current_bid),
    guide_price: num(s.guide_price),
    pricing_confidence: s.pricing_confidence,
    auction_house_id: s.auction_house_id ? Number(s.auction_house_id) : null,
    cost_items: s.costs
      .filter((c) => c.name.trim())
      .map((c) => ({
        name: c.name,
        category: c.category,
        estimated_amount: c.estimated_amount || "0",
        minimum_amount: num(c.minimum_amount),
        maximum_amount: num(c.maximum_amount),
      })),
    risk_signals: {
      category_marker: s.category_marker || null,
      stolen_marker: s.stolen_marker,
      outstanding_finance: s.finance_marker,
      mileage_discrepancy: s.mileage_discrepancy,
      imported: s.imported,
      mot_fail_count: Number(s.mot_fail_count) || 0,
      dangerous_defect_count: Number(s.dangerous_defect_count) || 0,
      non_runner: s.runner_status === "NON_RUNNER",
      condition_grade: Number(s.condition_grade) || null,
      missing_service_history: s.missing_service_history,
      mileage: Number(s.mileage) || null,
    },
  };
}
