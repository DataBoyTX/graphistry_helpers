// User types
export type UserRole = 'admin' | 'user'

export interface User {
  id: string
  email: string
  name: string | null
  role: UserRole
  picture_url: string | null
  is_active: boolean
  created_at: string
  updated_at: string
  has_google_tokens?: boolean
}

// Customer types
export interface Customer {
  id: string
  company_name: string
  contact_name: string | null
  email: string | null
  phone: string | null
  address_line1: string | null
  address_line2: string | null
  city: string | null
  state: string | null
  postal_code: string | null
  country: string
  tax_id: string | null
  is_international: boolean
  notes: string | null
  created_by: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CustomerCreate {
  company_name: string
  contact_name?: string
  email?: string
  phone?: string
  address_line1?: string
  address_line2?: string
  city?: string
  state?: string
  postal_code?: string
  country?: string
  tax_id?: string
  is_international?: boolean
  notes?: string
}

// Product types
export type ProductCategory = 'license' | 'service' | 'training' | 'subscription'
export type BillingPeriod = 'one-time' | 'monthly' | 'quarterly' | 'annual'

export interface Product {
  id: string
  sku: string | null
  name: string
  description: string | null
  category: ProductCategory
  unit_price: number
  currency: string
  is_recurring: boolean
  billing_period: BillingPeriod
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ProductCreate {
  name: string
  sku?: string
  description?: string
  category?: ProductCategory
  unit_price: number
  currency?: string
  is_recurring?: boolean
  billing_period?: BillingPeriod
}

// Quote types
export type QuoteStatus = 'draft' | 'pending_approval' | 'approved' | 'sent' | 'accepted' | 'rejected' | 'expired'
export type TemplateType = 'us' | 'international'

export interface QuoteLineItem {
  id: string
  quote_id: string
  product_id: string | null
  description: string
  quantity: number
  unit_price: number
  discount_percent: number
  line_total: number
  sort_order: number
}

export interface QuoteLineItemCreate {
  product_id?: string
  description: string
  quantity: number
  unit_price: number
  discount_percent?: number
}

export interface Quote {
  id: string
  quote_number: string
  customer_id: string
  created_by: string
  status: QuoteStatus
  subtotal: number
  discount_percent: number
  discount_amount: number
  tax_rate: number
  tax_amount: number
  total: number
  currency: string
  template_type: TemplateType
  terms_and_conditions: string | null
  notes: string | null
  valid_until: string | null
  requires_approval: boolean
  approved_by: string | null
  approved_at: string | null
  drive_doc_id: string | null
  drive_pdf_id: string | null
  gmail_draft_id: string | null
  created_at: string
  updated_at: string
  sent_at: string | null
}

export interface QuoteDetail extends Quote {
  line_items: QuoteLineItem[]
  customer: Customer | null
}

export interface QuoteCreate {
  customer_id: string
  template_type?: TemplateType
  currency?: string
  discount_percent?: number
  tax_rate?: number
  terms_and_conditions?: string
  notes?: string
  valid_until?: string
  line_items: QuoteLineItemCreate[]
}

// Order types
export type OrderStatus = 'pending' | 'confirmed' | 'fulfilled' | 'cancelled'

export interface Order {
  id: string
  order_number: string
  quote_id: string
  customer_id: string
  status: OrderStatus
  accepted_at: string | null
  accepted_by: string | null
  subtotal: number
  discount_amount: number
  tax_amount: number
  total: number
  currency: string
  notes: string | null
  created_at: string
  updated_at: string
}

export interface OrderDetail extends Order {
  customer: Customer | null
}

// API response types
export interface PaginatedResponse<T> {
  total: number
  page: number
  page_size: number
}

export interface CustomersResponse extends PaginatedResponse<Customer> {
  customers: Customer[]
}

export interface ProductsResponse {
  products: Product[]
  total: number
}

export interface QuotesResponse extends PaginatedResponse<Quote> {
  quotes: Quote[]
}

export interface OrdersResponse extends PaginatedResponse<Order> {
  orders: Order[]
}
