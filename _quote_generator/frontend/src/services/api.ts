import axios from 'axios'
import type {
  User,
  Customer,
  CustomerCreate,
  CustomersResponse,
  Product,
  ProductCreate,
  ProductsResponse,
  Quote,
  QuoteDetail,
  QuoteCreate,
  QuotesResponse,
  Order,
  OrderDetail,
  OrdersResponse,
  OrderStatus,
} from '../types'

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
})

// Auth
export const auth = {
  getGoogleAuthUrl: async () => {
    const { data } = await api.get<{ authorization_url: string }>('/auth/google')
    return data.authorization_url
  },

  getCurrentUser: async () => {
    const { data } = await api.get<User>('/auth/me')
    return data
  },

  logout: async () => {
    await api.post('/auth/logout')
  },
}

// Users
export const users = {
  list: async () => {
    const { data } = await api.get<{ users: User[]; total: number }>('/users')
    return data
  },

  updateRole: async (userId: string, role: 'admin' | 'user') => {
    const { data } = await api.patch<User>(`/users/${userId}/role`, { role })
    return data
  },
}

// Customers
export const customers = {
  list: async (params?: { search?: string; page?: number; page_size?: number }) => {
    const { data } = await api.get<CustomersResponse>('/customers', { params })
    return data
  },

  get: async (id: string) => {
    const { data } = await api.get<Customer>(`/customers/${id}`)
    return data
  },

  create: async (customer: CustomerCreate) => {
    const { data } = await api.post<Customer>('/customers', customer)
    return data
  },

  update: async (id: string, customer: Partial<CustomerCreate>) => {
    const { data } = await api.put<Customer>(`/customers/${id}`, customer)
    return data
  },

  delete: async (id: string) => {
    await api.delete(`/customers/${id}`)
  },
}

// Products
export const products = {
  list: async (params?: { search?: string; category?: string; active_only?: boolean }) => {
    const { data } = await api.get<ProductsResponse>('/products', { params })
    return data
  },

  get: async (id: string) => {
    const { data } = await api.get<Product>(`/products/${id}`)
    return data
  },

  create: async (product: ProductCreate) => {
    const { data } = await api.post<Product>('/products', product)
    return data
  },

  update: async (id: string, product: Partial<ProductCreate>) => {
    const { data } = await api.put<Product>(`/products/${id}`, product)
    return data
  },

  delete: async (id: string) => {
    await api.delete(`/products/${id}`)
  },

  importFromSheets: async (spreadsheetId: string, sheetName: string = 'Products') => {
    const { data } = await api.post<ProductsResponse>('/products/import', {
      spreadsheet_id: spreadsheetId,
      sheet_name: sheetName,
    })
    return data
  },
}

// Quotes
export const quotes = {
  list: async (params?: { status?: string; customer_id?: string; page?: number; page_size?: number }) => {
    const { data } = await api.get<QuotesResponse>('/quotes', { params })
    return data
  },

  get: async (id: string) => {
    const { data } = await api.get<QuoteDetail>(`/quotes/${id}`)
    return data
  },

  create: async (quote: QuoteCreate) => {
    const { data } = await api.post<QuoteDetail>('/quotes', quote)
    return data
  },

  update: async (id: string, quote: Partial<QuoteCreate>) => {
    const { data } = await api.put<QuoteDetail>(`/quotes/${id}`, quote)
    return data
  },

  delete: async (id: string) => {
    await api.delete(`/quotes/${id}`)
  },

  submit: async (id: string) => {
    const { data } = await api.post<Quote>(`/quotes/${id}/submit`)
    return data
  },

  approve: async (id: string, notes?: string) => {
    const { data } = await api.post<Quote>(`/quotes/${id}/approve`, { notes })
    return data
  },

  reject: async (id: string, notes?: string) => {
    const { data } = await api.post<Quote>(`/quotes/${id}/reject`, { notes })
    return data
  },

  accept: async (id: string, acceptedBy: string, notes?: string) => {
    const { data } = await api.post<{ order_id: string; order_number: string }>(`/quotes/${id}/accept`, {
      accepted_by: acceptedBy,
      notes,
    })
    return data
  },

  send: async (id: string) => {
    const { data } = await api.post<{
      message: string
      drive_pdf_link: string
      drive_doc_link: string
      gmail_draft_id: string
    }>(`/quotes/${id}/send`)
    return data
  },

  downloadPdf: async (id: string) => {
    const response = await api.get(`/quotes/${id}/pdf`, { responseType: 'blob' })
    return response.data as Blob
  },
}

// Orders
export const orders = {
  list: async (params?: { status?: string; customer_id?: string; page?: number; page_size?: number }) => {
    const { data } = await api.get<OrdersResponse>('/orders', { params })
    return data
  },

  get: async (id: string) => {
    const { data } = await api.get<OrderDetail>(`/orders/${id}`)
    return data
  },

  updateStatus: async (id: string, status: OrderStatus, notes?: string) => {
    const { data } = await api.patch<Order>(`/orders/${id}/status`, { status, notes })
    return data
  },
}

// Dashboard
export interface DashboardStats {
  total_customers: number
  total_products: number
  total_quotes: number
  total_orders: number
  draft_quotes: number
  pending_quotes: number
  sent_quotes: number
  pending_orders: number
  confirmed_orders: number
  total_revenue: number
  monthly_revenue: number
  quote_pipeline: number
}

export interface RecentActivityItem {
  id: string
  type: string
  reference: string
  description: string
  status: string
  amount: number
  currency: string
  timestamp: string
}

export const dashboard = {
  getStats: async () => {
    const { data } = await api.get<DashboardStats>('/dashboard/stats')
    return data
  },

  getRecentActivity: async (limit = 10) => {
    const { data } = await api.get<RecentActivityItem[]>('/dashboard/recent', { params: { limit } })
    return data
  },
}

export default api
