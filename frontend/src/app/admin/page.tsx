'use client'

import { useEffect, useState } from 'react'
import { admin } from '@/lib/api'
import { Package, ShoppingCart, Users, DollarSign, TrendingUp, Clock } from 'lucide-react'

export default function AdminDashboard() {
  const [stats, setStats] = useState<any>(null)
  const [recentOrders, setRecentOrders] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDashboard()
  }, [])

  const loadDashboard = async () => {
    try {
      const [statsData, ordersData] = await Promise.all([
        admin.dashboard(),
        admin.orders({ limit: 5 }),
      ])
      setStats(statsData)
      setRecentOrders(ordersData)
    } catch (error) {
      console.error('Failed to load dashboard:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-8"></div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  const statCards = [
    { label: 'Total Products', value: stats?.total_products || 0, icon: Package, color: 'bg-blue-500' },
    { label: 'Total Orders', value: stats?.total_orders || 0, icon: ShoppingCart, color: 'bg-green-500' },
    { label: 'Total Customers', value: stats?.total_customers || 0, icon: Users, color: 'bg-purple-500' },
    { label: 'Total Revenue', value: `৳${(stats?.total_revenue || 0).toLocaleString()}`, icon: DollarSign, color: 'bg-yellow-500' },
  ]

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        {statCards.map((stat, index) => (
          <div key={index} className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">{stat.label}</p>
                <p className="text-2xl font-bold mt-1">{stat.value}</p>
              </div>
              <div className={`p-3 rounded-lg ${stat.color}`}>
                <stat.icon className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Recent Orders */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Recent Orders</h2>
          <a href="/admin/orders" className="text-primary-600 hover:underline text-sm">View All</a>
        </div>
        
        {recentOrders.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No orders yet</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b text-left text-sm text-gray-600">
                  <th className="pb-3 font-medium">Order #</th>
                  <th className="pb-3 font-medium">Customer</th>
                  <th className="pb-3 font-medium">Total</th>
                  <th className="pb-3 font-medium">Status</th>
                  <th className="pb-3 font-medium">Date</th>
                </tr>
              </thead>
              <tbody>
                {recentOrders.map((order) => (
                  <tr key={order.id} className="border-b last:border-0">
                    <td className="py-3 font-medium">{order.order_number}</td>
                    <td className="py-3">{order.guest_name}</td>
                    <td className="py-3">৳{order.total_amount.toLocaleString()}</td>
                    <td className="py-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        order.status === 'delivered' ? 'bg-green-100 text-green-800' :
                        order.status === 'cancelled' ? 'bg-red-100 text-red-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        {order.status}
                      </span>
                    </td>
                    <td className="py-3 text-sm text-gray-500">
                      {new Date(order.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
        <a href="/admin/products" className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
          <Package className="w-8 h-8 text-blue-500 mb-3" />
          <h3 className="font-semibold">Manage Products</h3>
          <p className="text-sm text-gray-600 mt-1">Add, edit, or remove products</p>
        </a>
        <a href="/admin/orders" className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
          <ShoppingCart className="w-8 h-8 text-green-500 mb-3" />
          <h3 className="font-semibold">Process Orders</h3>
          <p className="text-sm text-gray-600 mt-1">View and update order status</p>
        </a>
        <a href="/admin/coupons" className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
          <TrendingUp className="w-8 h-8 text-purple-500 mb-3" />
          <h3 className="font-semibold">Create Coupons</h3>
          <p className="text-sm text-gray-600 mt-1">Manage discount codes</p>
        </a>
      </div>
    </div>
  )
}
