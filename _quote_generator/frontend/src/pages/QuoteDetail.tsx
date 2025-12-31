import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { quotes } from '../services/api'
import { useAuth } from '../hooks/useAuth'
import QuoteBuilder from '../components/quotes/QuoteBuilder'
import {
  ArrowLeft,
  Send,
  Check,
  X,
  Pencil,
  FileText,
  Trash2,
  Download,
  CheckCircle,
} from 'lucide-react'

export default function QuoteDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { isAdmin } = useAuth()
  const queryClient = useQueryClient()
  const [isEditing, setIsEditing] = useState(false)

  const { data: quote, isLoading } = useQuery({
    queryKey: ['quote', id],
    queryFn: () => quotes.get(id!),
    enabled: !!id && id !== 'new',
  })

  const submitMutation = useMutation({
    mutationFn: () => quotes.submit(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quote', id] })
      queryClient.invalidateQueries({ queryKey: ['quotes'] })
    },
  })

  const approveMutation = useMutation({
    mutationFn: () => quotes.approve(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quote', id] })
      queryClient.invalidateQueries({ queryKey: ['quotes'] })
    },
  })

  const rejectMutation = useMutation({
    mutationFn: () => quotes.reject(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quote', id] })
      queryClient.invalidateQueries({ queryKey: ['quotes'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => quotes.delete(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quotes'] })
      navigate('/quotes')
    },
  })

  const sendMutation = useMutation({
    mutationFn: () => quotes.send(id!),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['quote', id] })
      queryClient.invalidateQueries({ queryKey: ['quotes'] })
      alert(`Quote sent successfully!\n\nGmail draft created. Check your Gmail drafts folder to review and send.\n\nDrive PDF: ${data.drive_pdf_link}`)
    },
    onError: (error: any) => {
      alert(error.response?.data?.detail || 'Failed to send quote')
    },
  })

  const acceptMutation = useMutation({
    mutationFn: (data: { acceptedBy: string; notes?: string }) =>
      quotes.accept(id!, data.acceptedBy, data.notes),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['quote', id] })
      queryClient.invalidateQueries({ queryKey: ['quotes'] })
      queryClient.invalidateQueries({ queryKey: ['orders'] })
      alert(`Quote accepted!\n\nOrder ${data.order_number} has been created.`)
      navigate(`/orders`)
    },
    onError: (error: any) => {
      alert(error.response?.data?.detail || 'Failed to accept quote')
    },
  })

  const formatCurrency = (amount: number, currency = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(amount)
  }

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      draft: 'bg-gray-100 text-gray-800',
      pending_approval: 'bg-yellow-100 text-yellow-800',
      approved: 'bg-blue-100 text-blue-800',
      sent: 'bg-indigo-100 text-indigo-800',
      accepted: 'bg-green-100 text-green-800',
      rejected: 'bg-red-100 text-red-800',
      expired: 'bg-gray-100 text-gray-800',
    }
    return colors[status] || 'bg-gray-100 text-gray-800'
  }

  // New quote - show builder
  if (id === 'new') {
    return <QuoteBuilder />
  }

  // Loading
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  // Not found
  if (!quote) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Quote not found</p>
      </div>
    )
  }

  // Editing draft - show builder
  if (isEditing && quote.status === 'draft') {
    return <QuoteBuilder existingQuote={quote} />
  }

  // View mode
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate('/quotes')} className="p-2 hover:bg-gray-100 rounded">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{quote.quote_number}</h1>
            <p className="text-sm text-gray-500">
              {quote.customer?.company_name || 'Unknown Customer'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`px-3 py-1 text-sm font-medium rounded-full ${getStatusColor(
              quote.status
            )} capitalize`}
          >
            {quote.status.replace('_', ' ')}
          </span>

          {/* Draft actions */}
          {quote.status === 'draft' && (
            <>
              <button onClick={() => setIsEditing(true)} className="btn-secondary">
                <Pencil className="w-4 h-4 mr-2" />
                Edit
              </button>
              <button
                onClick={() => submitMutation.mutate()}
                disabled={submitMutation.isPending || !quote.line_items?.length}
                className="btn-primary"
              >
                <Send className="w-4 h-4 mr-2" />
                Submit
              </button>
              <button
                onClick={() => {
                  if (confirm('Are you sure you want to delete this quote?')) {
                    deleteMutation.mutate()
                  }
                }}
                className="btn-danger"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </>
          )}

          {/* Pending approval actions (admin only) */}
          {quote.status === 'pending_approval' && isAdmin && (
            <>
              <button
                onClick={() => approveMutation.mutate()}
                disabled={approveMutation.isPending}
                className="btn-primary"
              >
                <Check className="w-4 h-4 mr-2" />
                Approve
              </button>
              <button
                onClick={() => {
                  const reason = prompt('Rejection reason (optional):')
                  if (reason !== null) {
                    rejectMutation.mutate()
                  }
                }}
                disabled={rejectMutation.isPending}
                className="btn-danger"
              >
                <X className="w-4 h-4 mr-2" />
                Reject
              </button>
            </>
          )}

          {/* Approved actions */}
          {quote.status === 'approved' && (
            <>
              <button
                onClick={() => sendMutation.mutate()}
                disabled={sendMutation.isPending}
                className="btn-primary"
              >
                <Send className="w-4 h-4 mr-2" />
                {sendMutation.isPending ? 'Sending...' : 'Send to Customer'}
              </button>
              <a
                href={`/api/quotes/${quote.id}/pdf`}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-secondary"
              >
                <Download className="w-4 h-4 mr-2" />
                Download PDF
              </a>
            </>
          )}

          {/* Sent actions */}
          {quote.status === 'sent' && (
            <>
              <button
                onClick={() => {
                  const acceptedBy = prompt('Who is accepting this quote? (Customer name or email)')
                  if (acceptedBy) {
                    const notes = prompt('Any notes? (optional)')
                    acceptMutation.mutate({ acceptedBy, notes: notes || undefined })
                  }
                }}
                disabled={acceptMutation.isPending}
                className="btn-primary"
              >
                <CheckCircle className="w-4 h-4 mr-2" />
                {acceptMutation.isPending ? 'Accepting...' : 'Accept Quote'}
              </button>
              <button
                onClick={() => sendMutation.mutate()}
                disabled={sendMutation.isPending}
                className="btn-secondary"
              >
                <Send className="w-4 h-4 mr-2" />
                {sendMutation.isPending ? 'Resending...' : 'Resend'}
              </button>
              <a
                href={`/api/quotes/${quote.id}/pdf`}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-secondary"
              >
                <Download className="w-4 h-4 mr-2" />
                Download PDF
              </a>
            </>
          )}

          {/* Accepted quote - show order link */}
          {quote.status === 'accepted' && (
            <a
              href={`/api/quotes/${quote.id}/pdf`}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-secondary"
            >
              <Download className="w-4 h-4 mr-2" />
              Download PDF
            </a>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Line Items */}
          <div className="card">
            <div className="px-6 py-4 border-b">
              <h2 className="text-lg font-medium text-gray-900">Line Items</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Description
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      Qty
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      Unit Price
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      Discount
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      Total
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {quote.line_items?.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                        No line items
                      </td>
                    </tr>
                  ) : (
                    quote.line_items?.map((item) => (
                      <tr key={item.id}>
                        <td className="px-6 py-4 text-sm text-gray-900">{item.description}</td>
                        <td className="px-6 py-4 text-sm text-gray-900 text-right">
                          {item.quantity}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-900 text-right">
                          {formatCurrency(item.unit_price, quote.currency)}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-900 text-right">
                          {item.discount_percent > 0 ? `${item.discount_percent}%` : '-'}
                        </td>
                        <td className="px-6 py-4 text-sm font-medium text-gray-900 text-right">
                          {formatCurrency(item.line_total, quote.currency)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Notes */}
          {quote.notes && (
            <div className="card p-6">
              <h3 className="text-sm font-medium text-gray-900 mb-2">Notes</h3>
              <p className="text-sm text-gray-600 whitespace-pre-wrap">{quote.notes}</p>
            </div>
          )}

          {/* Terms */}
          {quote.terms_and_conditions && (
            <div className="card p-6">
              <h3 className="text-sm font-medium text-gray-900 mb-2">Terms & Conditions</h3>
              <p className="text-sm text-gray-600 whitespace-pre-wrap">
                {quote.terms_and_conditions}
              </p>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Summary */}
          <div className="card p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Summary</h3>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Subtotal</span>
                <span className="text-gray-900">
                  {formatCurrency(quote.subtotal, quote.currency)}
                </span>
              </div>
              {quote.discount_amount > 0 && (
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Discount ({quote.discount_percent}%)</span>
                  <span className="text-red-600">
                    -{formatCurrency(quote.discount_amount, quote.currency)}
                  </span>
                </div>
              )}
              {quote.tax_amount > 0 && (
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">
                    {quote.template_type === 'us' ? 'Tax' : 'VAT'} ({quote.tax_rate}%)
                  </span>
                  <span className="text-gray-900">
                    {formatCurrency(quote.tax_amount, quote.currency)}
                  </span>
                </div>
              )}
              <div className="border-t pt-3 flex justify-between">
                <span className="font-medium text-gray-900">Total</span>
                <span className="font-bold text-gray-900 text-lg">
                  {formatCurrency(quote.total, quote.currency)}
                </span>
              </div>
            </div>
          </div>

          {/* Customer Info */}
          {quote.customer && (
            <div className="card p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Customer</h3>
              <div className="space-y-2 text-sm">
                <p className="font-medium text-gray-900">{quote.customer.company_name}</p>
                {quote.customer.contact_name && (
                  <p className="text-gray-600">{quote.customer.contact_name}</p>
                )}
                {quote.customer.email && <p className="text-gray-600">{quote.customer.email}</p>}
                {quote.customer.city && (
                  <p className="text-gray-600">
                    {[quote.customer.city, quote.customer.state, quote.customer.country]
                      .filter(Boolean)
                      .join(', ')}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Quote Details */}
          <div className="card p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Details</h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Template</span>
                <span className="text-gray-900 capitalize">{quote.template_type}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Currency</span>
                <span className="text-gray-900">{quote.currency}</span>
              </div>
              {quote.valid_until && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Valid Until</span>
                  <span className="text-gray-900">
                    {new Date(quote.valid_until).toLocaleDateString()}
                  </span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-gray-500">Created</span>
                <span className="text-gray-900">
                  {new Date(quote.created_at).toLocaleDateString()}
                </span>
              </div>
              {quote.approved_at && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Approved</span>
                  <span className="text-gray-900">
                    {new Date(quote.approved_at).toLocaleDateString()}
                  </span>
                </div>
              )}
              {quote.sent_at && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Sent</span>
                  <span className="text-gray-900">
                    {new Date(quote.sent_at).toLocaleDateString()}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Approval Info */}
          {quote.requires_approval && (
            <div className="card p-6 bg-yellow-50 border-yellow-200">
              <h3 className="text-sm font-medium text-yellow-800 mb-2">Requires Approval</h3>
              <p className="text-sm text-yellow-700">
                This quote requires admin approval before it can be sent.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
