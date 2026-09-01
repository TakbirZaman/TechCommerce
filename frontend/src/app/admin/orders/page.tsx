'use client'

import { useEffect, useState } from 'react'
import { admin } from '@/lib/api'
import { Search, Eye, ChevronDown } from 'lucide-react'

export default function AdminOrdersPage() {
  const [orders, setOrders] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [selectedOrder, setSelectedOrder] = useState<any>(null)

  useEffect(() => {
    loadOrders()
  }, [statusFilter])

  const loadOrders = async () => {
    setLoading(true)
    try {
      const data = await admin.orders({
        status: statusFilter || undefined,
        search: searchQuery || undefined,
      })
      setOrders(data.orders || [])
    } catch (error) {
      console.error('Failed to load orders:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = () => {
    loadOrders()
  }

  const updateStatus = async (orderId: number, status: string) => {
    try {
      await admin.updateOrder(orderId, { order_status: status })
      setOrders(prev =>
        prev.map(o => o.id === orderId ? { ...o, order_status: status } : o)
      )
      if (selectedOrder?.id === orderId) {
        setSelectedOrder(prev => ({ ...prev, order_status: status }))
      }
    } catch (error: any) {
      alert(error.message || 'Failed to update status')
    }
  }

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'bg-yellow-100 text-yellow-800',
      confirmed: 'bg-blue-100 text-blue-800',
      processing: 'bg-purple-100 text-purple-800',
      shipped: 'bg-indigo-100 text-indigo-800',
      delivered: 'bg-green-100 text-green-800',
      cancelled: 'bg-red-100 text-red-800',
    }
    return colors[status] || 'bg-gray-100 text-gray-800'
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Orders</h1>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-md p-4 mb-6">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px] relative">
            <input
              type="text"
              placeholder="Search by order # or customer..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="w-full pl-10 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">All Status</option>
            <option value="pending">Pending</option>
            <option value="confirmed">Confirmed</option>
            <option value="processing">Processing</option>
            <option value="shipped">Shipped</option>
            <option value="delivered">Delivered</option>
            <option value="cancelled">Cancelled</option>
          </select>
          <button
            onClick={handleSearch}
            className="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200"
          >
            Search
          </button>
        </div>
      </div>

      <div className="flex gap-6">
        {/* Orders List */}
        <div className={`${selectedOrder ? 'w-1/2' : 'w-full'} transition-all`}>
          <div className="bg-white rounded-lg shadow-md overflow-hidden">
            {loading ? (
              <div className="p-8 text-center text-gray-500">Loading...</div>
            ) : orders.length === 0 ? (
              <div className="p-8 text-center text-gray-500">No orders found</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="bg-gray-50 border-b text-left text-sm text-gray-600">
                      <th className="p-4 font-medium">Order #</th>
                      <th className="p-4 font-medium">Customer</th>
                      <th className="p-4 font-medium">Total</th>
                      <th className="p-4 font-medium">Status</th>
                      <th className="p-4 font-medium">Date</th>
                      <th className="p-4 font-medium">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {orders.map((order) => (
                      <tr
                        key={order.id}
                        className={`border-b last:border-0 hover:bg-gray-50 cursor-pointer ${
                          selectedOrder?.id === order.id ? 'bg-primary-50' : ''
                        }`}
                        onClick={() => setSelectedOrder(order)}
                      >
                        <td className="p-4 font-medium">{order.order_number}</td>
                        <td className="p-4">{order.guest_name}</td>
                        <td className="p-4 font-medium">৳{order.total_amount.toLocaleString()}</td>
                        <td className="p-4">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(order.order_status)}`}>
                            {order.order_status}
                          </span>
                        </td>
                        <td className="p-4 text-sm text-gray-500">
                          {new Date(order.created_at).toLocaleDateString()}
                        </td>
                        <td className="p-4">
                          <button className="text-primary-600 hover:underline text-sm">
                            View
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Order Detail */}
        {selectedOrder && (
          <div className="w-1/2">
            <div className="bg-white rounded-lg shadow-md p-6 sticky top-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold">{selectedOrder.order_number}</h2>
                <button
                  onClick={() => setSelectedOrder(null)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  ×
                </button>
              </div>

              <div className="space-y-4 mb-6">
                <div>
                  <p className="text-sm text-gray-600">Customer</p>
                  <p className="font-medium">{selectedOrder.guest_name}</p>
                  <p className="text-sm text-gray-600">{selectedOrder.guest_email}</p>
                  <p className="text-sm text-gray-600">{selectedOrder.guest_phone}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Shipping Address</p>
                  <p className="text-sm">{selectedOrder.shipping_address}</p>
                  <p className="text-sm">{selectedOrder.shipping_city}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Payment</p>
                  <p className="text-sm capitalize">{selectedOrder.payment_method}</p>
                  <p className="text-sm">৳{selectedOrder.total_amount.toLocaleString()}</p>
                </div>
              </div>

              {/* Status Update */}
              <div className="border-t pt-4 mb-4">
                <p className="text-sm font-medium mb-2">Update Status</p>
                <div className="flex gap-2">
                  {['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled'].map((status) => (
                    <button
                      key={status}
                      onClick={() => updateStatus(selectedOrder.id, status)}
                      className={`px-3 py-1 rounded text-xs font-medium ${
                        selectedOrder.order_status === status
                          ? getStatusColor(status)
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      {status}
                    </button>
                  ))}
                </div>
              </div>

              {/* Items */}
              <div className="border-t pt-4">
                <p className="text-sm font-medium mb-2">Items</p>
                <div className="space-y-2">
                  {selectedOrder.items?.map((item: any) => (
                    <div key={item.id} className="flex justify-between text-sm">
                      <span>{item.product_name} × {item.quantity}</span>
                      <span>৳{item.subtotal.toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
