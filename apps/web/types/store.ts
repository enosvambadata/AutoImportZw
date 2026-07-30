// Public storefront types (mirror app/schemas/storefront.py). Money fields are Decimal-as-string.

export interface PublicCarSummary {
  slug: string;
  status: string;
  headline: string;
  make: string;
  model: string;
  derivative: string | null;
  model_year: number | null;
  mileage: number | null;
  fuel_type: string | null;
  transmission: string | null;
  colour: string | null;
  currency: string;
  landed_total: string;
  dest_city: string | null;
  dest_country: string;
  has_video: boolean;
  thumb: string | null;
}

export interface PublicMotTest {
  date: string | null;
  result: string | null;
  odometer: number | null;
  unit: string | null;
  expiry: string | null;
  advisories: number;
  dangerous: number;
}

export interface PublicMot {
  expiry: string | null;
  pass_count: number;
  fail_count: number;
  advisory_count: number;
  dangerous_defect_count: number;
  tests: PublicMotTest[];
}

export interface PublicLanded {
  currency: string;
  vehicle_price: string;
  auction_fees: string;
  uk_transport: string;
  ocean_freight: string;
  import_duty: string;
  import_surtax: string;
  import_vat: string;
  inland_transport: string;
  estimated_repairs: string;
  service_fee: string;
  total: string;
  dest_country: string;
  dest_port: string | null;
  dest_city: string | null;
}

export interface PublicCarDetail extends PublicCarSummary {
  blurb: string | null;
  video_url: string | null;
  images: string[];
  category_marker: string | null;
  registration: string | null;
  notes: string | null;
  mot: PublicMot | null;
  landed: PublicLanded;
}

export interface PublicStats {
  delivered: number;
  available: number;
  destinations: string[];
}
