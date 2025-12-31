import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { quotes, customers, products } from '../../services/api'
import { Plus, Trash2, Save, ArrowLeft, Package } from 'lucide-react'
import type {
  Customer,
  Product,
  QuoteCreate,
  QuoteDetail,
  QuoteLineItemCreate,
  TemplateType,
} from '../../types'

interface LineItemRow {
  id: string
  product_id: string | null
  description: string
  quantity: number
  unit_price: number
  discount_percent: number
}

const generateId = () => Math.random().toString(36).substring(2, 9)

const emptyLineItem = (): LineItemRow => ({
  id: generateId(),
  product_id: null,
  description: '',
  quantity: 1,
  unit_price: 0,
  discount_percent: 0,
})

interface QuoteBuilderProps {
  existingQuote?: QuoteDetail
}

export default function QuoteBuilder({ existingQuote }: QuoteBuilderProps) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Form state
  const [customerId, setCustomerId] = useState(existingQuote?.customer_id || '')
  const [templateType, setTemplateType] = useState<TemplateType>(
    existingQuote?.template_type || 'us'
  )
  const [currency, setCurrency] = useState(existingQuote?.currency || 'USD')
  const [discountPercent, setDiscountPercent] = useState(existingQuote?.discount_percent || 0)
  const [taxRate, setTaxRate] = useState(existingQuote?.tax_rate || 0)
  const [validUntil, setValidUntil] = useState(existingQuote?.valid_until || '')
  const [notes, setNotes] = useState(existingQuote?.notes || '')
  const [termsAndConditions, setTermsAndConditions] = useState(
    existingQuote?.terms_and_conditions || ''
  )
  const [lineItems, setLineItems] = useState<LineItemRow[]>(() => {
    if (existingQuote?.line_items?.length) {
      return existingQuote.line_items.map((item) => ({
        id: item.id,
        product_id: item.product_id,
        description: item.description,
        quantity: item.quantity,
        unit_price: item.unit_price,
        discount_percent: item.discount_percent,
      }))
    }
    return [emptyLineItem()]
  })

  // Fetch customers and products
  const { data: customersData } = useQuery({
    queryKey: ['customers'],
    queryFn: () => customers.list({ page_size: 100 }),
  })

  const { data: productsData } = useQuery({
    queryKey: ['products'],
    queryFn: () => products.list({ active_only: true }),
  })

  // Create/update mutations
  const createMutation = useMutation({
    mutationFn: quotes.create,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['quotes'] })
      navigate(`/quotes/${data.id}`)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<QuoteCreate> }) =>
      quotes.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quotes'] })
      queryClient.invalidateQueries({ queryKey: ['quote', existingQuote?.id] })
    },
  })

  // Calculate totals
  const calculations = useMemo(() => {
    const subtotal = lineItems.reduce((sum, item) => {
      const lineTotal = item.quantity * item.unit_price * (1 - item.discount_percent / 100)
      return sum + lineTotal
    }, 0)

    const discountAmount = subtotal * (discountPercent / 100)
    const afterDiscount = subtotal - discountAmount
    const taxAmount = afterDiscount * (taxRate / 100)
    const total = afterDiscount + taxAmount

    return { subtotal, discountAmount, taxAmount, total }
  }, [lineItems, discountPercent, taxRate])

  // Line item handlers
  const addLineItem = () => {
    setLineItems([...lineItems, emptyLineItem()])
  }

  const removeLineItem = (id: string) => {
    if (lineItems.length > 1) {
      setLineItems(lineItems.filter((item) => item.id !== id))
    }
  }

  const updateLineItem = (id: string, field: keyof LineItemRow, value: any) => {
    setLineItems(
      lineItems.map((item) => (item.id === id ? { ...item, [field]: value } : item))
    )
  }

  const selectProduct = (lineItemId: string, productId: string) => {
    const product = productsData?.products.find((p) => p.id === productId)
    if (product) {
      setLineItems(
        lineItems.map((item) =>
          item.id === lineItemId
            ? {
                ...item,
                product_id: productId,
                description: product.name,
                unit_price: product.unit_price,
              }
            : item
        )
      )
    }
  }

  // Set default tax rate based on template type
  useEffect(() => {
    if (templateType === 'us') {
      setTaxRate(0) // Can be configured
    } else {
      setTaxRate(20) // Default VAT
    }
  }, [templateType])

  // Handle customer selection to auto-set template type
  const handleCustomerChange = (customerId: string) => {
    setCustomerId(customerId)
    const customer = customersData?.customers.find((c) => c.id === customerId)
    if (customer) {
      setTemplateType(customer.is_international ? 'international' : 'us')
    }
  }

  // Format currency
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(amount)
  }

  // Handle save
  const handleSave = () => {
    if (!customerId) {
      alert('Please select a customer')
      return
    }

    if (lineItems.every((item) => !item.description)) {
      alert('Please add at least one line item')
      return
    }

    const quoteData: QuoteCreate = {
      customer_id: customerId,
      template_type: templateType,
      currency,
      discount_percent: discountPercent,
      tax_rate: taxRate,
      valid_until: validUntil || undefined,
      notes: notes || undefined,
      terms_and_conditions: termsAndConditions || undefined,
      line_items: lineItems
        .filter((item) => item.description)
        .map((item) => ({
          product_id: item.product_id || undefined,
          description: item.description,
          quantity: item.quantity,
          unit_price: item.unit_price,
          discount_percent: item.discount_percent,
        })),
    }

    if (existingQuote) {
      updateMutation.mutate({ id: existingQuote.id, data: quoteData })
    } else {
      createMutation.mutate(quoteData)
    }
  }

  const isLoading = createMutation.isPending || updateMutation.isPending

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate('/quotes')} className="p-2 hover:bg-gray-100 rounded">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <h1 className="text-2xl font-bold text-gray-900">
            {existingQuote ? `Edit ${existingQuote.quote_number}` : 'New Quote'}
          </h1>
        </div>
        <button onClick={handleSave} disabled={isLoading} className="btn-primary">
          <Save className="w-4 h-4 mr-2" />
          {isLoading ? 'Saving...' : 'Save Quote'}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Customer & Settings */}
          <div className="card p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Quote Details</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="label">Customer *</label>
                <select
                  value={customerId}
                  onChange={(e) => handleCustomerChange(e.target.value)}
                  className="input"
                  required
                >
                  <option value="">Select a customer...</option>
                  {customersData?.customers.map((customer) => (
                    <option key={customer.id} value={customer.id}>
                      {customer.company_name}
                      {customer.is_international ? ' (International)' : ''}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">Template</label>
                <select
                  value={templateType}
                  onChange={(e) => setTemplateType(e.target.value as TemplateType)}
                  className="input"
                >
                  <option value="us">US (Sales Tax)</option>
                  <option value="international">International (VAT)</option>
                </select>
              </div>
              <div>
                <label className="label">Currency</label>
                <select value={currency} onChange={(e) => setCurrency(e.target.value)} className="input">
                  <option value="USD">USD - US Dollar</option>
                  <option value="EUR">EUR - Euro</option>
                  <option value="GBP">GBP - British Pound</option>
                </select>
              </div>
              <div>
                <label className="label">Valid Until</label>
                <input
                  type="date"
                  value={validUntil}
                  onChange={(e) => setValidUntil(e.target.value)}
                  className="input"
                />
              </div>
            </div>
          </div>

          {/* Line Items */}
          <div className="card">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-lg font-medium text-gray-900">Line Items</h2>
              <button onClick={addLineItem} className="btn-secondary text-sm">
                <Plus className="w-4 h-4 mr-1" />
                Add Item
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-12">
                      Product
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Description
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-24">
                      Qty
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-32">
                      Unit Price
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-24">
                      Discount
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase w-32">
                      Total
                    </th>
                    <th className="px-4 py-3 w-12"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {lineItems.map((item, index) => {
                    const lineTotal =
                      item.quantity * item.unit_price * (1 - item.discount_percent / 100)
                    return (
                      <tr key={item.id}>
                        <td className="px-4 py-3">
                          <select
                            value={item.product_id || ''}
                            onChange={(e) => selectProduct(item.id, e.target.value)}
                            className="input text-sm py-1.5"
                          >
                            <option value="">-</option>
                            {productsData?.products.map((product) => (
                              <option key={product.id} value={product.id}>
                                {product.sku || product.name.substring(0, 15)}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="px-4 py-3">
                          <input
                            type="text"
                            value={item.description}
                            onChange={(e) => updateLineItem(item.id, 'description', e.target.value)}
                            placeholder="Item description"
                            className="input text-sm py-1.5"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <input
                            type="number"
                            value={item.quantity}
                            onChange={(e) =>
                              updateLineItem(item.id, 'quantity', parseFloat(e.target.value) || 0)
                            }
                            min="0"
                            step="0.01"
                            className="input text-sm py-1.5 text-right"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <input
                            type="number"
                            value={item.unit_price}
                            onChange={(e) =>
                              updateLineItem(item.id, 'unit_price', parseFloat(e.target.value) || 0)
                            }
                            min="0"
                            step="0.01"
                            className="input text-sm py-1.5 text-right"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center">
                            <input
                              type="number"
                              value={item.discount_percent}
                              onChange={(e) =>
                                updateLineItem(
                                  item.id,
                                  'discount_percent',
                                  parseFloat(e.target.value) || 0
                                )
                              }
                              min="0"
                              max="100"
                              className="input text-sm py-1.5 text-right w-16"
                            />
                            <span className="ml-1 text-gray-500 text-sm">%</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right text-sm font-medium text-gray-900">
                          {formatCurrency(lineTotal)}
                        </td>
                        <td className="px-4 py-3">
                          <button
                            onClick={() => removeLineItem(item.id)}
                            disabled={lineItems.length === 1}
                            className="p-1 text-gray-400 hover:text-red-600 disabled:opacity-30"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Notes & Terms */}
          <div className="card p-6 space-y-4">
            <div>
              <label className="label">Notes (visible on quote)</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                placeholder="Add any notes for the customer..."
                className="input"
              />
            </div>
            <div>
              <label className="label">Terms & Conditions</label>
              <textarea
                value={termsAndConditions}
                onChange={(e) => setTermsAndConditions(e.target.value)}
                rows={4}
                placeholder="Payment terms, delivery terms, etc..."
                className="input"
              />
            </div>
          </div>
        </div>

        {/* Sidebar - Summary */}
        <div className="space-y-6">
          <div className="card p-6 sticky top-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Summary</h3>

            {/* Discount & Tax inputs */}
            <div className="space-y-3 mb-4 pb-4 border-b">
              <div>
                <label className="label text-xs">Quote Discount (%)</label>
                <input
                  type="number"
                  value={discountPercent}
                  onChange={(e) => setDiscountPercent(parseFloat(e.target.value) || 0)}
                  min="0"
                  max="100"
                  step="0.01"
                  className="input text-sm py-1.5"
                />
              </div>
              <div>
                <label className="label text-xs">
                  {templateType === 'us' ? 'Sales Tax (%)' : 'VAT (%)'}
                </label>
                <input
                  type="number"
                  value={taxRate}
                  onChange={(e) => setTaxRate(parseFloat(e.target.value) || 0)}
                  min="0"
                  max="100"
                  step="0.01"
                  className="input text-sm py-1.5"
                />
              </div>
            </div>

            {/* Totals */}
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Subtotal</span>
                <span className="text-gray-900">{formatCurrency(calculations.subtotal)}</span>
              </div>
              {discountPercent > 0 && (
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Discount ({discountPercent}%)</span>
                  <span className="text-red-600">-{formatCurrency(calculations.discountAmount)}</span>
                </div>
              )}
              {taxRate > 0 && (
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">
                    {templateType === 'us' ? 'Tax' : 'VAT'} ({taxRate}%)
                  </span>
                  <span className="text-gray-900">{formatCurrency(calculations.taxAmount)}</span>
                </div>
              )}
              <div className="border-t pt-3 flex justify-between">
                <span className="font-medium text-gray-900">Total</span>
                <span className="font-bold text-gray-900 text-xl">
                  {formatCurrency(calculations.total)}
                </span>
              </div>
            </div>
          </div>

          {/* Selected Customer Info */}
          {customerId && (
            <div className="card p-6">
              <h3 className="text-sm font-medium text-gray-900 mb-3">Customer</h3>
              {(() => {
                const customer = customersData?.customers.find((c) => c.id === customerId)
                if (!customer) return null
                return (
                  <div className="text-sm space-y-1">
                    <p className="font-medium text-gray-900">{customer.company_name}</p>
                    {customer.contact_name && (
                      <p className="text-gray-600">{customer.contact_name}</p>
                    )}
                    {customer.email && <p className="text-gray-600">{customer.email}</p>}
                    {customer.city && (
                      <p className="text-gray-600">
                        {[customer.city, customer.state, customer.country]
                          .filter(Boolean)
                          .join(', ')}
                      </p>
                    )}
                  </div>
                )
              })()}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
