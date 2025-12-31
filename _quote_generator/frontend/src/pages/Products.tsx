import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { products } from '../services/api'
import { Plus, Search, Pencil, Trash2, Upload } from 'lucide-react'
import type { Product, ProductCreate, ProductCategory, BillingPeriod } from '../types'

const categories: { value: ProductCategory; label: string }[] = [
  { value: 'license', label: 'License' },
  { value: 'service', label: 'Service' },
  { value: 'training', label: 'Training' },
  { value: 'subscription', label: 'Subscription' },
]

const billingPeriods: { value: BillingPeriod; label: string }[] = [
  { value: 'one-time', label: 'One-time' },
  { value: 'monthly', label: 'Monthly' },
  { value: 'quarterly', label: 'Quarterly' },
  { value: 'annual', label: 'Annual' },
]

export default function Products() {
  const [search, setSearch] = useState('')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isImportModalOpen, setIsImportModalOpen] = useState(false)
  const [editingProduct, setEditingProduct] = useState<Product | null>(null)
  const [spreadsheetId, setSpreadsheetId] = useState('')
  const [sheetName, setSheetName] = useState('Products')
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['products', { search }],
    queryFn: () => products.list({ search: search || undefined }),
  })

  const createMutation = useMutation({
    mutationFn: products.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
      setIsModalOpen(false)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ProductCreate> }) =>
      products.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
      setEditingProduct(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: products.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
  })

  const importMutation = useMutation({
    mutationFn: () => products.importFromSheets(spreadsheetId, sheetName),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
      setIsImportModalOpen(false)
      setSpreadsheetId('')
      setSheetName('Products')
      alert(`Successfully imported ${data.total} products`)
    },
    onError: (error: any) => {
      alert(error.response?.data?.detail || 'Failed to import products')
    },
  })

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const productData: ProductCreate = {
      name: formData.get('name') as string,
      sku: formData.get('sku') as string || undefined,
      description: formData.get('description') as string || undefined,
      category: formData.get('category') as ProductCategory,
      unit_price: parseFloat(formData.get('unit_price') as string),
      currency: formData.get('currency') as string || 'USD',
      is_recurring: formData.get('is_recurring') === 'true',
      billing_period: formData.get('billing_period') as BillingPeriod,
    }

    if (editingProduct) {
      updateMutation.mutate({ id: editingProduct.id, data: productData })
    } else {
      createMutation.mutate(productData)
    }
  }

  const formatCurrency = (amount: number, currency = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(amount)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Products</h1>
          <p className="text-sm text-gray-500">Manage your products and services</p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => setIsImportModalOpen(true)} className="btn-secondary">
            <Upload className="w-4 h-4 mr-2" />
            Import from Sheets
          </button>
          <button onClick={() => setIsModalOpen(true)} className="btn-primary">
            <Plus className="w-4 h-4 mr-2" />
            Add Product
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          placeholder="Search products..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input pl-10"
        />
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Product
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                SKU
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Category
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Price
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Billing
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {isLoading ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                  Loading...
                </td>
              </tr>
            ) : data?.products.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                  No products found
                </td>
              </tr>
            ) : (
              data?.products.map((product) => (
                <tr key={product.id}>
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900">{product.name}</div>
                    {product.description && (
                      <div className="text-sm text-gray-500 truncate max-w-xs">
                        {product.description}
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {product.sku || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-800 capitalize">
                      {product.category}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatCurrency(product.unit_price, product.currency)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 capitalize">
                    {product.billing_period.replace('-', ' ')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button
                      onClick={() => setEditingProduct(product)}
                      className="text-primary-600 hover:text-primary-900 mr-3"
                    >
                      <Pencil className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => {
                        if (confirm('Are you sure you want to deactivate this product?')) {
                          deleteMutation.mutate(product.id)
                        }
                      }}
                      className="text-red-600 hover:text-red-900"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Modal */}
      {(isModalOpen || editingProduct) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
            <form onSubmit={handleSubmit}>
              <div className="px-6 py-4 border-b">
                <h3 className="text-lg font-medium text-gray-900">
                  {editingProduct ? 'Edit Product' : 'Add Product'}
                </h3>
              </div>
              <div className="px-6 py-4 space-y-4">
                <div>
                  <label className="label">Name *</label>
                  <input
                    name="name"
                    defaultValue={editingProduct?.name}
                    required
                    className="input"
                  />
                </div>
                <div>
                  <label className="label">SKU</label>
                  <input
                    name="sku"
                    defaultValue={editingProduct?.sku || ''}
                    className="input"
                  />
                </div>
                <div>
                  <label className="label">Description</label>
                  <textarea
                    name="description"
                    defaultValue={editingProduct?.description || ''}
                    rows={3}
                    className="input"
                  />
                </div>
                <div>
                  <label className="label">Category</label>
                  <select
                    name="category"
                    defaultValue={editingProduct?.category || 'service'}
                    className="input"
                  >
                    {categories.map((cat) => (
                      <option key={cat.value} value={cat.value}>
                        {cat.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="label">Price *</label>
                    <input
                      name="unit_price"
                      type="number"
                      step="0.01"
                      min="0"
                      defaultValue={editingProduct?.unit_price || 0}
                      required
                      className="input"
                    />
                  </div>
                  <div>
                    <label className="label">Currency</label>
                    <select
                      name="currency"
                      defaultValue={editingProduct?.currency || 'USD'}
                      className="input"
                    >
                      <option value="USD">USD</option>
                      <option value="EUR">EUR</option>
                      <option value="GBP">GBP</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="label">Billing Period</label>
                  <select
                    name="billing_period"
                    defaultValue={editingProduct?.billing_period || 'one-time'}
                    className="input"
                  >
                    {billingPeriods.map((bp) => (
                      <option key={bp.value} value={bp.value}>
                        {bp.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="px-6 py-4 border-t flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setIsModalOpen(false)
                    setEditingProduct(null)
                  }}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  {editingProduct ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Import Modal */}
      {isImportModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
            <div className="px-6 py-4 border-b">
              <h3 className="text-lg font-medium text-gray-900">Import Products from Google Sheets</h3>
            </div>
            <div className="px-6 py-4 space-y-4">
              <div>
                <label className="label">Spreadsheet ID *</label>
                <input
                  value={spreadsheetId}
                  onChange={(e) => setSpreadsheetId(e.target.value)}
                  placeholder="e.g., 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
                  className="input"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Found in the Google Sheets URL after /d/
                </p>
              </div>
              <div>
                <label className="label">Sheet Name</label>
                <input
                  value={sheetName}
                  onChange={(e) => setSheetName(e.target.value)}
                  placeholder="Products"
                  className="input"
                />
              </div>
              <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-600">
                <p className="font-medium mb-2">Expected columns:</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>Name (required)</li>
                  <li>SKU</li>
                  <li>Description</li>
                  <li>Category (license, service, training, subscription)</li>
                  <li>Unit Price</li>
                  <li>Currency (USD, EUR, GBP)</li>
                  <li>Is Recurring (true/false)</li>
                  <li>Billing Period (one-time, monthly, quarterly, annual)</li>
                </ul>
              </div>
            </div>
            <div className="px-6 py-4 border-t flex justify-end gap-3">
              <button
                type="button"
                onClick={() => {
                  setIsImportModalOpen(false)
                  setSpreadsheetId('')
                  setSheetName('Products')
                }}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={() => importMutation.mutate()}
                disabled={!spreadsheetId || importMutation.isPending}
                className="btn-primary disabled:opacity-50"
              >
                {importMutation.isPending ? 'Importing...' : 'Import'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
