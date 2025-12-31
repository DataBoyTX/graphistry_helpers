import { useQuery } from '@tanstack/react-query'
import { dashboard, quotes, orders } from '../services/api'
import {
  FileText,
  ShoppingCart,
  Users,
  TrendingUp,
  DollarSign,
  Clock,
  Package,
} from 'lucide-react'
import { Link } from 'react-router-dom'

export default function Dashboard() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => dashboard.getStats(),
  })

  const { data: quotesData } = useQuery({
    queryKey: ['quotes', { page: 1, page_size: 5 }],
    queryFn: () => quotes.list({ page: 1, page_size: 5 }),
  })

  const { data: ordersData } = useQuery({
    queryKey: ['orders', { page: 1, page_size: 5 }],
    queryFn: () => orders.list({ page: 1, page_size: 5 }),
  })

  const formatCurrency = (amount: number, currency = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
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
      pending: 'bg-yellow-100 text-yellow-800',
      confirmed: 'bg-blue-100 text-blue-800',
      fulfilled: 'bg-green-100 text-green-800',
      cancelled: 'bg-red-100 text-red-800',
    }
    return colors[status] || 'bg-gray-100 text-gray-800'
  }

  const mainStats = [
    {
      name: 'Total Revenue',
      value: stats ? formatCurrency(stats.total_revenue) : '$0',
      icon: DollarSign,
      color: 'bg-green-500',
      description: 'All-time order revenue',
    },
    {
      name: 'Monthly Revenue',
      value: stats ? formatCurrency(stats.monthly_revenue) : '$0',
      icon: TrendingUp,
      color: 'bg-blue-500',
      description: 'Last 30 days',
    },
    {
      name: 'Quote Pipeline',
      value: stats ? formatCurrency(stats.quote_pipeline) : '$0',
      icon: Clock,
      color: 'bg-purple-500',
      description: 'Approved & sent quotes',
    },
    {
      name: 'Total Orders',
      value: stats?.total_orders || 0,
      icon: ShoppingCart,
      color: 'bg-orange-500',
      description: `${stats?.pending_orders || 0} pending`,
    },
  ]

  const secondaryStats = [
    {
      name: 'Quotes',
      value: stats?.total_quotes || 0,
      icon: FileText,
      color: 'text-blue-600',
      href: '/quotes',
      details: [
        { label: 'Draft', value: stats?.draft_quotes || 0 },
        { label: 'Pending', value: stats?.pending_quotes || 0 },
        { label: 'Sent', value: stats?.sent_quotes || 0 },
      ],
    },
    {
      name: 'Orders',
      value: stats?.total_orders || 0,
      icon: Package,
      color: 'text-green-600',
      href: '/orders',
      details: [
        { label: 'Pending', value: stats?.pending_orders || 0 },
        { label: 'Confirmed', value: stats?.confirmed_orders || 0 },
      ],
    },
    {
      name: 'Customers',
      value: stats?.total_customers || 0,
      icon: Users,
      color: 'text-purple-600',
      href: '/customers',
      details: [],
    },
  ]

  if (statsLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500">Overview of your quotes and orders</p>
      </div>

      {/* Main Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {mainStats.map((stat) => (
          <div key={stat.name} className="card p-6">
            <div className="flex items-center">
              <div className={`${stat.color} p-3 rounded-lg`}>
                <stat.icon className="w-6 h-6 text-white" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">{stat.name}</p>
                <p className="text-2xl font-semibold text-gray-900">{stat.value}</p>
                <p className="text-xs text-gray-400">{stat.description}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Secondary Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {secondaryStats.map((stat) => (
          <Link key={stat.name} to={stat.href} className="card p-6 hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center">
                <stat.icon className={`w-5 h-5 ${stat.color} mr-2`} />
                <span className="text-sm font-medium text-gray-500">{stat.name}</span>
              </div>
              <span className="text-2xl font-bold text-gray-900">{stat.value}</span>
            </div>
            {stat.details.length > 0 && (
              <div className="flex gap-4 text-sm">
                {stat.details.map((detail) => (
                  <div key={detail.label} className="text-gray-600">
                    <span className="font-medium">{detail.value}</span>{' '}
                    <span className="text-gray-400">{detail.label}</span>
                  </div>
                ))}
              </div>
            )}
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Recent Quotes */}
        <div className="card">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-medium text-gray-900">Recent Quotes</h2>
              <Link to="/quotes" className="text-sm text-primary-600 hover:text-primary-700">
                View all
              </Link>
            </div>
          </div>
          <div className="divide-y divide-gray-200">
            {quotesData?.quotes.length === 0 ? (
              <div className="px-6 py-8 text-center text-gray-500">
                No quotes yet.{' '}
                <Link to="/quotes/new" className="text-primary-600 hover:text-primary-700">
                  Create your first quote
                </Link>
              </div>
            ) : (
              quotesData?.quotes.map((quote) => (
                <Link
                  key={quote.id}
                  to={`/quotes/${quote.id}`}
                  className="block px-6 py-4 hover:bg-gray-50"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{quote.quote_number}</p>
                      <p className="text-sm text-gray-500">
                        {formatCurrency(quote.total, quote.currency)}
                      </p>
                    </div>
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded-full capitalize ${getStatusColor(
                        quote.status
                      )}`}
                    >
                      {quote.status.replace('_', ' ')}
                    </span>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>

        {/* Recent Orders */}
        <div className="card">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-medium text-gray-900">Recent Orders</h2>
              <Link to="/orders" className="text-sm text-primary-600 hover:text-primary-700">
                View all
              </Link>
            </div>
          </div>
          <div className="divide-y divide-gray-200">
            {ordersData?.orders.length === 0 ? (
              <div className="px-6 py-8 text-center text-gray-500">
                No orders yet. Orders are created when quotes are accepted.
              </div>
            ) : (
              ordersData?.orders.map((order) => (
                <Link key={order.id} to={`/orders/${order.id}`} className="block px-6 py-4 hover:bg-gray-50">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{order.order_number}</p>
                      <p className="text-sm text-gray-500">
                        {formatCurrency(order.total, order.currency)}
                      </p>
                    </div>
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded-full capitalize ${getStatusColor(
                        order.status
                      )}`}
                    >
                      {order.status}
                    </span>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
