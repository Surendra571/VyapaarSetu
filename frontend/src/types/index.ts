export type UserRole = 'ROLE_RETAILER' | 'ROLE_ORDER_DESK';

export interface User {
  id: string;
  phone_number: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  retailer?: RetailerProfile;
}

export interface RetailerProfile {
  id: string;
  user_id: string;
  retailer_code: string;
  store_name: string;
  owner_name: string;
  address: string;
  city: string;
  gst_number: string | null;
  credit_limit: number;
  outstanding_amount: number;
  available_credit: number;
  is_credit_locked: boolean;
  pricing_tier: string;
}

export interface Product {
  id: string;
  sku_code: string;
  name: string;
  brand: string;
  category: string;
  pack_size_description: string;
  units_per_case: number;
  default_dealer_price: number;
  mrp: number;
  price_basis: string;
  image_url: string;
  is_active: boolean;
  stock_cases?: number;
  available_cases: number;
  contracted_price?: number;
  effective_price?: number;
  active_schemes?: Scheme[];
}

export interface SchemeRule {
  id: string;
  rule_type: 'BUY_X_GET_Y_FREE' | 'PERCENTAGE_DISCOUNT' | 'SLAB_DISCOUNT';
  qualifying_product_id?: string;
  min_quantity: number;
  free_product_id?: string;
  free_product_name?: string;
  free_quantity?: number;
  discount_percentage?: number;
}

export interface Scheme {
  id: string;
  scheme_code: string;
  name: string;
  description: string;
  is_active: boolean;
  is_stackable: boolean;
  priority: number;
  rules?: SchemeRule[];
}

export interface CartItem {
  product: Product;
  quantityCases: number;
  unitPrice: number;
}

export interface OrderPreviewItem {
  product_id: string;
  sku_code: string;
  product_name: string;
  quantity_cases: number;
  unit_price: number;
  total_price: number;
  is_free_item: boolean;
  applied_scheme_name?: string;
}

export interface FreeGood {
  product_id: string;
  sku_code: string;
  product_name: string;
  free_cases: number;
  scheme_name: string;
}

export interface OrderPreviewResponse {
  subtotal: number;
  discount_amount: number;
  tax_amount: number;
  final_total: number;
  free_goods: FreeGood[];
  available_credit: number;
  credit_limit_exceeded: boolean;
  has_conflicting_schemes: boolean;
  warnings: string[];
  items: OrderPreviewItem[];
}

export type OrderStatus =
  | 'SUBMITTED'
  | 'UNDER_REVIEW'
  | 'CREDIT_HOLD'
  | 'APPROVED'
  | 'REJECTED'
  | 'DISPATCHED'
  | 'EXPORTED';

export interface OrderItem {
  id: string;
  product_id: string;
  sku_code: string;
  product_name: string;
  quantity_cases: number;
  unit_price: number;
  total_price: number;
  is_free_good: boolean;
  scheme_name?: string;
}

export interface Order {
  id: string;
  order_number: string;
  retailer_id: string;
  retailer_name: string;
  retailer_code: string;
  status: OrderStatus;
  subtotal_amount: number;
  discount_amount: number;
  total_amount: number;
  item_count: number;
  created_at: string;
  approved_at?: string;
  rejected_at?: string;
  rejection_reason?: string;
  notes?: string;
  items: OrderItem[];
  raw_message_text?: string;
  source_type: 'WEB_APP' | 'AI_WHATSAPP';
}

export interface SKUAlternative {
  sku_code: string;
  product_name: string;
  product_id: string;
  similarity_score: number;
  dealer_price: number;
  available_cases: number;
}

export interface AICapturedLine {
  line_index: number;
  original_phrase: string;
  matched_sku_code: string | null;
  matched_product_name: string | null;
  matched_product_id: string | null;
  quantity: number;
  unit: 'CASE' | 'PIECE' | 'UNRESOLVED';
  confidence_score: number;
  confidence_label: 'HIGH' | 'MEDIUM' | 'LOW';
  alternatives: SKUAlternative[];
  unit_clarification_required: boolean;
  resolution_status: 'RESOLVED' | 'NEEDS_REVIEW' | 'REJECTED';
}

export interface AICaptureResponse {
  session_id: string;
  raw_message: string;
  overall_confidence: number;
  lines: AICapturedLine[];
  unresolved_count: number;
}
