import type { Product, Scheme } from './types';

const envUrl = (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || '').trim().replace(/\/+$/, '');
const API_BASE = envUrl
  ? (envUrl.endsWith('/api/v1') ? envUrl : `${envUrl}/api/v1`)
  : '/api/v1';
const TOKEN_KEY = 'vyapaar_access_token';

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface RetailerPrice {
  product_id: string;
  sku_code: string;
  product_name: string;
  effective_price: number | string;
  price_basis: string;
  is_custom_price: boolean;
  units_per_case: number;
  price_notice: string;
}

export interface RetailerProfile {
  id: string;
  retailer_code: string;
  store_name: string;
  owner_name: string;
  city: string;
  credit_limit: number | string;
  outstanding_amount: number | string;
  available_credit: number | string;
  is_credit_locked: boolean;
  pricing_tier: string;
}

export interface AuthUser {
  id: string;
  phone_number: string;
  full_name: string;
  role: 'ROLE_RETAILER' | 'ROLE_ORDER_DESK';
  is_active: boolean;
  retailer?: RetailerProfile | null;
}

export interface CaptureLine {
  id: string;
  line_number: number;
  raw_line_text: string;
  parsed_item_name: string;
  parsed_quantity: number;
  parsed_uom: string;
  language: string;
  unit_clarification_needed: boolean;
  clarification_prompt?: string | null;
  matched_product_id?: string | null;
  matched_sku_code?: string | null;
  matched_product_name?: string | null;
  confidence_score: number | string;
  confidence_level: 'HIGH' | 'MEDIUM' | 'LOW';
  is_uncertain: boolean;
  alternatives: {
    product_id: string;
    sku_code: string;
    product_name: string;
    pack_size: string;
    confidence: number | string;
  }[];
  resolved_product_id?: string | null;
  resolved_product_name?: string | null;
  resolved_quantity?: number | null;
  is_confirmed: boolean;
  saved_as_alias: boolean;
}

export interface CaptureSession {
  id: string;
  retailer_id: string;
  raw_text: string;
  status: string;
  model_version: string;
  lines: CaptureLine[];
  has_unconfirmed_lines: boolean;
  is_ai_fallback: boolean;
  ai_service_message?: string | null;
  notice: string;
}

export interface BenefitDetail {
  id: string;
  scheme_id: string;
  free_product_id: string;
  free_sku_code: string;
  free_product_name: string;
  free_qty: number;
  free_uom: string;
  benefit_type: string;
  calculation_snapshot?: Record<string, any>;
  created_at?: string;
}

export interface OrderLine {
  id: string;
  product_id: string;
  ordered_qty: number;
  approved_qty: number;
  uom_type: string;
  applied_scheme_id: string | null;
  scheme_discount_amount: number | string;
  free_item_qty: number;
  line_subtotal_excl_gst: number | string;
  product_name_snapshot: string;
  sku_code_snapshot: string;
  price_per_unit_snapshot: number | string;
  price_basis_snapshot: string;
  scheme_name_snapshot: string | null;
  discount_percentage_snapshot?: number | string | null;
  free_product_name_snapshot?: string | null;
  free_sku_code_snapshot?: string | null;
  benefits?: BenefitDetail[];
}

export interface OrderRecord {
  id: string;
  order_number: string;
  retailer_id: string;
  retailer_name?: string | null;
  retailer_code?: string | null;
  status: string;
  subtotal_excl_gst: number | string;
  credit_hold_reason?: string | null;
  desk_notes?: string | null;
  created_at: string;
  updated_at: string;
  item_count: number;
  items?: OrderLine[];
}

export interface PreviewLine {
  product_id: string;
  sku_code: string;
  product_name: string;
  requested_qty: number;
  available_stock: number;
  is_stock_sufficient: boolean;
  unit_price_excl_gst: number | string;
  price_basis: string;
  applied_scheme_name?: string | null;
  discount_amount_excl_gst: number | string;
  free_goods_qty: number;
  free_goods_product_name?: string | null;
  line_subtotal_excl_gst: number | string;
  scheme_explanation?: string | null;
  has_scheme_conflict: boolean;
  scheme_conflict_note?: string | null;
  benefits?: BenefitDetail[];
}

export interface OrderPreview {
  lines: PreviewLine[];
  total_cases: number;
  subtotal_excl_gst: number | string;
  total_discount_excl_gst: number | string;
  all_free_goods?: BenefitDetail[];
  has_insufficient_stock: boolean;
  has_scheme_conflicts: boolean;
  credit_check: {
    credit_limit: number | string;
    current_outstanding: number | string;
    available_credit: number | string;
    proposed_order_amount: number | string;
    is_credit_breached: boolean;
    will_trigger_credit_hold: boolean;
    notice: string;
  };
  tax_notice: string;
}

export interface VanLoadingStoreBreakdown {
  store_name: string;
  retailer_code: string;
  order_number: string;
  quantity: number;
  uom: string;
}

export interface VanLoadingItem {
  product_id: string;
  sku_code: string;
  product_name: string;
  category: string;
  total_quantity: number;
  total_cases: number;
  total_units: number;
  purchased_quantity: number;
  free_quantity: number;
  store_breakdowns: VanLoadingStoreBreakdown[];
}

export interface VanLoadingListResponse {
  generated_at: string;
  approved_orders_count: number;
  date_range?: string | null;
  items: VanLoadingItem[];
}

export interface InactiveRetailerItem {
  retailer_id: string;
  store_name: string;
  retailer_code: string;
  phone_number?: string | null;
  credit_limit: number | string;
  current_exposure: number | string;
  last_confirmed_order_date?: string | null;
  days_since_last_order?: number | null;
  total_confirmed_orders: number;
  total_spend_excl_gst: number | string;
}

export interface InactiveRetailersResponse {
  threshold_days: number;
  inactive_retailers_count: number;
  total_retailers_count: number;
  items: InactiveRetailerItem[];
  page: number;
  page_size: number;
  total_pages: number;
}

export interface RepeatOrderLineDiff {
  product_id: string;
  sku_code: string;
  product_name: string;
  old_qty: number;
  new_qty: number;
  old_price: number | string;
  current_price: number | string;
  price_changed: boolean;
  old_subtotal: number | string;
  current_subtotal: number | string;
  stock_available: number;
  is_out_of_stock: boolean;
  schemes_changed: boolean;
  new_schemes: string[];
}

export interface RepeatOrderPreviewResponse {
  original_order_id: string;
  can_repeat: boolean;
  blocker_reason?: string | null;
  lines: RepeatOrderLineDiff[];
  original_subtotal_excl_gst: number | string;
  revalidated_subtotal_excl_gst: number | string;
  credit_limit: number | string;
  credit_exposure_current: number | string;
  available_credit: number | string;
  is_credit_blocked: boolean;
}

export interface SMSStatusResponse {
  provider_name: string;
  is_mock: boolean;
  rate_limit_window_seconds: number;
  max_attempts_per_window: number;
  lock_duration_minutes: number;
}

export interface ExportBatch {
  id: string;
  batch_number: string;
  order_count: number;
  total_amount_excl_gst: number | string;
  file_name: string;
  file_format: string;
  download_url: string;
  created_at: string;
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has('Content-Type') && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  const token = getToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json() as { detail?: string | { msg?: string }[] };
      if (typeof body.detail === 'string') message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((item) => item.msg).filter(Boolean).join('; ') || message;
    } catch {
      // Keep the HTTP status message when the server does not return JSON.
    }
    throw new Error(message);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  login: (phone_number: string, otp_code: string) =>
    request<{ access_token: string; user: AuthUser }>('/auth/demo-login', {
      method: 'POST',
      body: JSON.stringify({ phone_number, otp_code }),
    }),

  me: () => request<AuthUser>('/auth/me'),

  logout: () => request<{ status: string; message: string }>('/auth/logout', { method: 'POST' }),

  products: () => request<Paginated<Product>>('/products?page=1&page_size=100'),

  schemes: () => request<Scheme[]>('/schemes'),

  retailerPrices: () => request<RetailerPrice[]>('/retailers/me/prices'),

  previewOrder: (items: { product_id: string; quantity_cases: number }[]) =>
    request<OrderPreview>('/orders/preview', {
      method: 'POST',
      body: JSON.stringify({ items }),
    }),

  placeOrder: (
    items: { product_id: string; quantity_cases: number }[],
    delivery_notes: string,
    client_order_id?: string,
  ) =>
    request<OrderRecord>('/orders', {
      method: 'POST',
      body: JSON.stringify({ items, delivery_notes, client_order_id }),
    }),

  retailerOrders: () => request<Paginated<OrderRecord>>('/orders?page=1&page_size=100'),

  retailerOrderDetail: (id: string) => request<OrderRecord>(`/orders/${id}`),

  repeatOrderPreview: (id: string) =>
    request<RepeatOrderPreviewResponse>(`/orders/${id}/repeat-preview`, {
      method: 'POST',
    }),

  captureText: (raw_text: string) =>
    request<CaptureSession>('/ai-capture/text', {
      method: 'POST',
      body: JSON.stringify({ raw_text }),
    }),

  capturePhoto: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return request<CaptureSession>('/ai-capture/photo', {
      method: 'POST',
      body: formData,
    });
  },

  captureVoice: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return request<CaptureSession>('/ai-capture/voice', {
      method: 'POST',
      body: formData,
    });
  },

  reviewCaptureLine: (
    captureId: string,
    lineId: string,
    resolution: {
      resolved_product_id: string;
      resolved_quantity: number;
      resolved_uom: 'CASE' | 'PIECE';
      is_confirmed: boolean;
      save_as_retailer_alias: boolean;
      alias_phrase: string;
    },
  ) =>
    request<CaptureLine>(`/ai-capture/${captureId}/lines/${lineId}`, {
      method: 'PATCH',
      body: JSON.stringify(resolution),
    }),

  confirmCapture: (captureId: string) =>
    request<{ session_id: string; confirmed_lines_count: number; order_preview: OrderPreview }>(
      `/ai-capture/${captureId}/confirm`,
      { method: 'POST' },
    ),

  deskOrders: (status?: string) =>
    request<Paginated<OrderRecord>>(`/desk/orders?page=1&page_size=100${status ? `&status=${encodeURIComponent(status)}` : ''}`),

  deskOrderDetail: (id: string) => request<OrderRecord>(`/desk/orders/${id}`),

  approveOrder: (id: string, override_credit_hold: boolean) =>
    request<OrderRecord>(`/desk/orders/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({
        notes: 'Reviewed and approved by Order Desk',
        override_credit_hold,
      }),
    }),

  holdOrder: (id: string, reason: string) =>
    request<OrderRecord>(`/desk/orders/${id}/hold`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),

  vanLoadingList: (fromDate?: string, toDate?: string) => {
    const params = new URLSearchParams();
    if (fromDate) params.append('from_date', fromDate);
    if (toDate) params.append('to_date', toDate);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return request<VanLoadingListResponse>(`/desk/van-loading-list${qs}`);
  },

  downloadVanLoadingCsv: async (fromDate?: string, toDate?: string): Promise<Blob> => {
    const params = new URLSearchParams();
    if (fromDate) params.append('from_date', fromDate);
    if (toDate) params.append('to_date', toDate);
    const qs = params.toString() ? `?${params.toString()}` : '';
    const token = getToken();
    const response = await fetch(`${API_BASE}/desk/van-loading-list/export-csv${qs}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    if (!response.ok) throw new Error(`Could not download van loading CSV (${response.status})`);
    return response.blob();
  },

  inactiveRetailers: (days: number = 14, search?: string, page: number = 1, pageSize: number = 50) => {
    const params = new URLSearchParams({
      days: days.toString(),
      page: page.toString(),
      page_size: pageSize.toString(),
    });
    if (search) params.append('search', search);
    return request<InactiveRetailersResponse>(`/desk/retailers/inactive?${params.toString()}`);
  },

  downloadInactiveRetailersCsv: async (days: number = 14): Promise<Blob> => {
    const token = getToken();
    const response = await fetch(`${API_BASE}/desk/retailers/inactive/export-csv?days=${days}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    if (!response.ok) throw new Error(`Could not download inactive retailers CSV (${response.status})`);
    return response.blob();
  },

  smsStatus: () => request<SMSStatusResponse>('/auth/sms-status'),

  exportBatches: () => request<Paginated<ExportBatch>>('/desk/exports?page=1&page_size=100'),

  createExport: (order_ids?: string[]) =>
    request<ExportBatch>('/desk/exports', {
      method: 'POST',
      body: JSON.stringify(order_ids ? { order_ids } : {}),
    }),

  downloadExport: async (url: string): Promise<Blob> => {
    const token = getToken();
    const response = await fetch(url.startsWith('/api') ? url : `/api${url}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    if (!response.ok) throw new Error(`Could not download export (${response.status})`);
    return response.blob();
  },
};
