import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { customers } from '../services/api'
import { Plus, Search, Pencil, Trash2 } from 'lucide-react'
import type { Customer, CustomerCreate } from '../types'

export default function Customers() {
  const [search, setSearch] = useState('')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['customers', { search }],
    queryFn: () => customers.list({ search: search || undefined }),
  })

  const createMutation = useMutation({
    mutationFn: customers.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customers'] })
      setIsModalOpen(false)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CustomerCreate> }) =>
      customers.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customers'] })
      setEditingCustomer(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: customers.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customers'] })
    },
  })

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const customerData: CustomerCreate = {
      company_name: formData.get('company_name') as string,
      contact_name: formData.get('contact_name') as string || undefined,
      email: formData.get('email') as string || undefined,
      phone: formData.get('phone') as string || undefined,
      address_line1: formData.get('address_line1') as string || undefined,
      city: formData.get('city') as string || undefined,
      state: formData.get('state') as string || undefined,
      postal_code: formData.get('postal_code') as string || undefined,
      country: formData.get('country') as string || 'US',
      is_international: formData.get('country') !== 'US',
    }

    if (editingCustomer) {
      updateMutation.mutate({ id: editingCustomer.id, data: customerData })
    } else {
      createMutation.mutate(customerData)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Customers</h1>
          <p className="text-sm text-gray-500">Manage your customer contacts</p>
        </div>
        <button onClick={() => setIsModalOpen(true)} className="btn-primary">
          <Plus className="w-4 h-4 mr-2" />
          Add Customer
        </button>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          placeholder="Search customers..."
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
                Company
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Contact
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Email
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Location
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {isLoading ? (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                  Loading...
                </td>
              </tr>
            ) : data?.customers.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                  No customers found
                </td>
              </tr>
            ) : (
              data?.customers.map((customer) => (
                <tr key={customer.id}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">
                      {customer.company_name}
                    </div>
                    {customer.is_international && (
                      <span className="text-xs text-gray-500">International</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {customer.contact_name || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {customer.email || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {[customer.city, customer.state, customer.country].filter(Boolean).join(', ') || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button
                      onClick={() => setEditingCustomer(customer)}
                      className="text-primary-600 hover:text-primary-900 mr-3"
                    >
                      <Pencil className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => {
                        if (confirm('Are you sure you want to delete this customer?')) {
                          deleteMutation.mutate(customer.id)
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
      {(isModalOpen || editingCustomer) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
            <form onSubmit={handleSubmit}>
              <div className="px-6 py-4 border-b">
                <h3 className="text-lg font-medium text-gray-900">
                  {editingCustomer ? 'Edit Customer' : 'Add Customer'}
                </h3>
              </div>
              <div className="px-6 py-4 space-y-4">
                <div>
                  <label className="label">Company Name *</label>
                  <input
                    name="company_name"
                    defaultValue={editingCustomer?.company_name}
                    required
                    className="input"
                  />
                </div>
                <div>
                  <label className="label">Contact Name</label>
                  <input
                    name="contact_name"
                    defaultValue={editingCustomer?.contact_name || ''}
                    className="input"
                  />
                </div>
                <div>
                  <label className="label">Email</label>
                  <input
                    name="email"
                    type="email"
                    defaultValue={editingCustomer?.email || ''}
                    className="input"
                  />
                </div>
                <div>
                  <label className="label">Phone</label>
                  <input
                    name="phone"
                    defaultValue={editingCustomer?.phone || ''}
                    className="input"
                  />
                </div>
                <div>
                  <label className="label">Address</label>
                  <input
                    name="address_line1"
                    defaultValue={editingCustomer?.address_line1 || ''}
                    className="input"
                  />
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="label">City</label>
                    <input
                      name="city"
                      defaultValue={editingCustomer?.city || ''}
                      className="input"
                    />
                  </div>
                  <div>
                    <label className="label">State</label>
                    <input
                      name="state"
                      defaultValue={editingCustomer?.state || ''}
                      className="input"
                    />
                  </div>
                  <div>
                    <label className="label">Postal Code</label>
                    <input
                      name="postal_code"
                      defaultValue={editingCustomer?.postal_code || ''}
                      className="input"
                    />
                  </div>
                </div>
                <div>
                  <label className="label">Country</label>
                  <input
                    name="country"
                    defaultValue={editingCustomer?.country || 'US'}
                    className="input"
                  />
                </div>
              </div>
              <div className="px-6 py-4 border-t flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setIsModalOpen(false)
                    setEditingCustomer(null)
                  }}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  {editingCustomer ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
