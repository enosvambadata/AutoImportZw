// Shared types mirroring the API. Monetary values arrive as decimal strings.

export type Role = "ADMIN" | "BUYER" | "VIEWER";

export type Recommendation =
  | "STRONG_BUY"
  | "BUY"
  | "CONSIDER"
  | "HIGH_RISK"
  | "PASS"
  | "INCOMPLETE_DATA";

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface User {
  id: number;
  dealership_id: number;
  first_name: string;
  last_name: string;
  email: string;
  role: Role;
  active: boolean;
  created_at: string;
}

export interface Vehicle {
  id: number;
  registration: string | null;
  vin: string | null;
  make: string;
  model: string;
  derivative: string | null;
  model_year: number | null;
  mileage: number | null;
  fuel_type: string | null;
  transmission: string | null;
  colour: string | null;
  number_of_keys: number | null;
  category_marker: string | null;
  imported: boolean;
  data_source: string;
  history?: VehicleHistory | null;
}

export interface MotTest {
  date: string | null;
  result: string | null;
  odometer: number | null;
  unit: string | null;
  expiry: string | null;
  advisories: number;
  dangerous: number;
}

export interface VehicleHistory {
  id: number;
  mot_expiry: string | null;
  mot_tests: MotTest[];
  mot_pass_count: number;
  mot_fail_count: number;
  advisory_count: number;
  dangerous_defect_count: number;
  repeated_failures: boolean;
  mileage_discrepancy: boolean;
  finance_marker: boolean;
  stolen_marker: boolean;
  service_history_status: string | null;
  history_provider: string;
  data_retrieved_at: string | null;
}

export interface AuctionHouse {
  id: number;
  name: string;
  website: string | null;
  postcode: string | null;
  fee_calc_type: string;
  default_transport_estimate: string;
  active: boolean;
  fee_bands: FeeBand[];
}

export interface FeeBand {
  id?: number;
  label?: string | null;
  fixed_fee: string;
  percentage: string;
  minimum_fee: string | null;
  maximum_fee: string | null;
  lower_bound: string | null;
  upper_bound: string | null;
  vat_applicable: boolean;
  stated_inclusive: boolean;
}

export interface Listing {
  id: number;
  vehicle_id: number;
  auction_house_id: number;
  lot_number: string | null;
  auction_datetime: string | null;
  guide_price: string | null;
  condition_grade: number | null;
  runner_status: string | null;
  vat_status: string;
  listing_status: string;
  data_source: string;
  image_urls?: string[];
  spin_urls?: string[];
  vehicle?: Vehicle | null;
  auction_house?: AuctionHouse | null;
}

export interface CostItem {
  id?: number;
  name: string;
  category: string;
  estimated_amount: string;
  minimum_amount: string | null;
  maximum_amount: string | null;
  vat_treatment?: string;
  certainty?: string;
  notes?: string | null;
}

export interface RiskAssessment {
  id: number;
  scores: Record<string, number>;
  weighted_total: number;
  risk_level: RiskLevel;
  explanations: string[];
  warning_flags: string[];
  critical_flags: string[];
  suggested_risk_reserve: string;
}

export interface Appraisal {
  id: number;
  vehicle_id: number;
  auction_listing_id: number | null;
  appraiser_id: number;
  status: string;
  expected_retail_price: string | null;
  conservative_retail_price: string | null;
  optimistic_retail_price: string | null;
  expected_negotiated_discount: string;
  pricing_confidence: string;
  target_profit: string;
  risk_reserve: string;
  desired_roi: string;
  estimated_days_to_sell: number;
  current_bid: string | null;
  recommendation: Recommendation | null;
  confidence_score: string | null;
  safe_max_bid: string | null;
  absolute_max_bid: string | null;
  break_even_bid: string | null;
  expected_profit: string | null;
  pessimistic_profit: string | null;
  optimistic_profit: string | null;
  expected_roi: string | null;
  risk_level: RiskLevel | null;
  result_snapshot: EvaluationResult;
  created_at: string;
  updated_at: string;
  cost_items: CostItem[];
  comparables: unknown[];
  risk_assessment: RiskAssessment | null;
}

export interface BidLadderRung {
  label: string;
  hammer: string;
  fee: string;
  total_cash_required: string;
  expected_profit: string;
  worst_case_profit: string;
  roi_on_cash: string | null;
  margin: string | null;
  exceeds_absolute: boolean;
}

export interface Calculation {
  safe_max_bid: string;
  absolute_max_bid: string;
  break_even_bid: string;
  reference_hammer: string;
  expected_profit: string;
  pessimistic_profit: string;
  optimistic_profit: string;
  total_cash_invested: string;
  roi_on_cost: string | null;
  roi_on_hammer: string | null;
  margin: string | null;
  meets_target: boolean;
  meets_roi: boolean;
  fee_at_reference: string;
  bid_ladder: BidLadderRung[];
  sensitivity: {
    price_deltas: string[];
    cost_deltas: string[];
    profit_matrix: string[][];
    days_axis: number[];
    days_profit: string[];
    discount_axis: string[];
    discount_profit: string[];
  };
}

export interface RecommendationResult {
  decision: Recommendation;
  reasons: string[];
  positive_factors: string[];
  warning_factors: string[];
  missing_information: string[];
  next_action: string;
  confidence: "LOW" | "MEDIUM" | "HIGH";
}

export interface EvaluationResult {
  calculation: Calculation | null;
  risk: {
    scores: Record<string, number>;
    weighted_total: number;
    level: RiskLevel;
    explanations: string[];
    warning_flags: string[];
    critical_flags: string[];
    suggested_risk_reserve: string;
    policy_blocks: string[];
  };
  recommendation: RecommendationResult;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface DashboardData {
  vehicles_appraised: number;
  strong_buys_and_buys: number;
  passed_vehicles: number;
  average_expected_profit: string | null;
  average_actual_profit: string | null;
  average_days_in_stock: number | null;
  estimated_capital_required: string;
  profit_forecast: string;
  appraisal_to_purchase_conversion: string;
  recent_appraisals: Array<{
    id: number;
    recommendation: Recommendation | null;
    expected_profit: string | null;
    risk_level: RiskLevel | null;
    status: string;
    created_at: string;
  }>;
  vehicles_requiring_action: Array<{ id: number; recommendation: string | null; status: string }>;
}
