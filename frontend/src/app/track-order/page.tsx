'use client'

import { useState } from 'react'
import Link from 'next/link'
import { commerce } from '@/lib/api'
import { Package, Clock, CheckCircle, Truck, XCircle } from 'lucide-react'

const statusIcons: Record<string, any> = {
  pending: Clock,
  confirmed: CheckCircle,
  processing: Package,
  shipped: Truck,
  delivered: CheckCircle,
  cancelled: XCircle,
}

const statusColors: Record<string, string> = {
  pending: 'text-yellow-500 bg-yellow-100',
  confirmed: 'text-blue-500 bg-blue-100',
  processing: 'text-purple-500 bg-purple-100',
  shipped: 'text-indigo-500 bg-indigo-100',
  delivered: 'text-green-500 bg-green-100',
  cancelled: 'text-red-500 bg-red-100',
}

export default function TrackOrderPage() {
  const [orderNumber, setOrderNumber] = useState('')
  const [email, setEmail] = useState('')
  const [order, setOrder] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setOrder(null)
    
    try {
      const data = await commerce.trackOrder(orderNumber, email)
      setOrder(data)
    } catch (err: any) {
      setError(err.message || 'Order not found')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-BD', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Track Your Order</h1>

      {/* Search Form */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-8">
        <form onSubmit={handleSearch}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Order Number</label>
              <input
                type="text"
                required
                placeholder="e.g., ORD-20260901-XXXX"
                value={orderNumber}
                onChange={(e) => setOrderNumber(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                required
                placeholder="Your email address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="bg-primary-600 text-white px-6 py-2 rounded-lg hover:bg-primary-700 disabled:opacity-50"
          >
            {loading ? 'Tracking...' : 'Track Order'}
          </button>
        </form>
        {error && (
          <p className="mt-4 text-red-600">{error}</p>
        )}
      </div>

      {/* Order Details */}
      {order && (
        <div className="space-y-6">
          {/* Status Card */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-xl font-bold">{order.order_number}</h2>
                <p className="text-gray-500 text-sm">Placed on {formatDate(order.created_at)}</p>
              </div>
              <div className={`px-4 py-2 rounded-full font-medium ${statusColors[order.status] || 'text-gray-500 bg-gray-100'}`}>
                {order.status.charAt(0).toUpperCase() + order.status.slice(1)}
              </div>
            </div>

            {/* Timeline */}
            <div className="mt-6">
              <h3 className="font-semibold mb-4">Order Timeline</h3>
              <div className="space-y-4">
                {['pending', 'confirmed', 'processing', 'shipped', 'delivered'].map((step, index) => {
                  const isCompleted = ['pending', 'confirmed', 'processing', 'shipped', 'delivered'].indexOf(order.status) >= index
                  const Icon = statusIcons[step] || Clock
                  return (
                    <div key={step} className="flex items-center gap-4">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                        isCompleted ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-400'
                      }`}>
                        <Icon className="w-4 h-4" />
                      </div>
                      <div className={`flex-1 ${isCompleted ? 'text-gray-900' : 'text-gray-400'}`}>
                        <span className="font-medium capitalize">{step}</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Shipping Address */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="font-semibold mb-4">Shipping Address</h3>
            <div className="text-gray-700">
              <p>{order.guest_name}</p>
              <p>{order.shipping_address}</p>
              <p>{order.shipping_city}, {order.shipping_postal_code}</p>
              <p>Phone: {order.guest_phone}</p>
            </div>
          </div>

          {/* Order Items */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="font-semibold mb-4">Order Items</h3>
            <div className="space-y-3">
              {order.items.map((item: any) => (
                <div key={item.id} className="flex justify-between items-center py-2 border-b last:border-0">
                  <div>
                    <p className="font-medium">{item.product_name}</p>
                    <p className="text-sm text-gray-500">Qty: {item.quantity}</p>
                  </div>
                  <span className="font-medium">৳{item.subtotal.toLocaleString()}</span>
                </div>
              ))}
            </div>
            <div className="border-t mt-4 pt-4">
              <div className="flex justify-between text-lg font-bold">
                <span>Total</span>
                <span className="text-primary-600">৳{order.total_amount.toLocaleString()}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
