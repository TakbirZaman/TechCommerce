'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { auth } from '@/lib/api'
import { LayoutDashboard, Package, ShoppingCart, Users, Tag, Truck, Settings, LogOut, Menu, X } from 'lucide-react'

const navItems = [
  { href: '/admin', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/admin/products', label: 'Products', icon: Package },
  { href: '/admin/orders', label: 'Orders', icon: ShoppingCart },
  { href: '/admin/customers', label: 'Customers', icon: Users },
  { href: '/admin/coupons', label: 'Coupons', icon: Tag },
  { href: '/admin/delivery', label: 'Delivery Zones', icon: Truck },
]

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const [user, setUser] = useState<any>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // The login page lives INSIDE this layout — never guard it, or unauthenticated
  // visits get redirected to /admin/login in an infinite loop (40 me-requests/s).
  const isLoginPage = pathname === '/admin/login'

  useEffect(() => {
    if (!isLoginPage) loadUser()
  }, [isLoginPage])

  const loadUser = async () => {
    try {
      const data = await auth.me()
      if (!data || data.role === 'customer') {
        window.location.href = '/admin/login'
        return
      }
      setUser(data)
    } catch (error) {
      window.location.href = '/admin/login'
    }
  }

  const handleLogout = async () => {
    await auth.logout()
    window.location.href = '/admin/login'
  }

  if (!user) {
    if (isLoginPage) {
      // Bare render: no admin chrome (sidebar references user.* and would crash).
      return <>{children}</>
    }
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Mobile sidebar toggle */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50 bg-white shadow-sm p-4 flex items-center justify-between">
        <h1 className="font-bold text-primary-600">Admin Panel</h1>
        <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-2">
          {sidebarOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-40 w-64 bg-white shadow-md transform transition-transform duration-200 ease-in-out ${
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      } lg:translate-x-0`}>
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="p-6 border-b">
            <Link href="/admin" className="flex items-center">
              <span className="text-xl font-bold text-primary-600">Tech</span>
              <span className="text-xl font-bold text-gray-900">Commerce</span>
            </Link>
            <p className="text-xs text-gray-500 mt-1">Admin Panel</p>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1">
            {navItems.map((item) => {
              const isActive = pathname === item.href
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setSidebarOpen(false)}
                  className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-primary-100 text-primary-700'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  <item.icon className="w-5 h-5" />
                  <span>{item.label}</span>
                </Link>
              )
            })}
          </nav>

          {/* User Info */}
          <div className="p-4 border-t">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center">
                <span className="font-medium text-primary-700">
                  {user.full_name?.charAt(0) || 'A'}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-sm truncate">{user.full_name}</p>
                <p className="text-xs text-gray-500 truncate">{user.email}</p>
              </div>
            </div>
            <div className="flex gap-2">
              <Link
                href="/"
                className="flex-1 text-center py-2 text-sm border rounded-lg hover:bg-gray-50"
              >
                View Site
              </Link>
              <button
                onClick={handleLogout}
                className="flex items-center justify-center gap-2 py-2 px-3 text-sm text-red-600 border border-red-200 rounded-lg hover:bg-red-50"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="lg:ml-64 min-h-screen pt-16 lg:pt-0">
        {children}
      </main>
    </div>
  )
}
