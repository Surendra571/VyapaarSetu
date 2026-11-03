// VyapaarSetu Types definition entry point
export type UserRole = 'retailer' | 'order_desk' | 'admin';

export interface Product {
  id: string;
  sku: string;
  name: string;
  hindiName?: string;
  unit: string;
  casePack: number;
  dealerPrice: number;
  stockCases: number;
}

