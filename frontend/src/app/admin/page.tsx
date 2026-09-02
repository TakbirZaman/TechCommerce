'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import {
  AlertTriangle,
  ArrowRight,
  Banknote,
  CheckCircle2,
  Clock,
  Package,
  SearchX,
  ShoppingCart,
  Users,
} from 'lucide-react'
import { admin, type AdminAnalytics } from '@/lib/api'
import { FadeIn, Stagger, StaggerItem } from '@/components/motion'
import AnimatedNumber from '@/components/admin/AnimatedNumber'
import { ChartCardHeader, RevenueAreaChart, StatusDonut } from '@/components/admin/AnalyticsCharts'

/**
 * Admin analytics dashboard — powered by GET /api/v1/admin/analytics.
 * Defensive against missing response keys; 401/403 redirects to /admin/login
 * (consistent with the layout guard).
 */

const fmtBDT = (n: number) => `৳${Math.round(n || 0).toLocaleString()}`

// Backend order timestamps are UTC ("...Z"). Parse explicitly so a naive
// string without a zone marker still reads as UTC, not the viewer's local
// timezone (which would silently shift the displayed day).
const parseUtcDate = (iso: string) =>
  new Date(/[zZ]$|[+-]\d{2}:?\d{2}$/.test(iso) ? iso : `${iso}Z`)

const isAuthError = (message: string) =>
  /\b(401|403)\b/.test(message) ||
  /unauthorized|forbidden|not authenticated|not authorized|not enough permissions|permission denied|could not validate|credentials/i.test(message)

const ORDER_STATUS_STYLES: Record<string, string> = {
  pending: 'bg-amber-100 text-amber-800 ring-1 ring-amber-200',
  confirmed: 'bg-blue-100 text-blue-800 ring-1 ring-blue-200',
  processing: 'bg-violet-100 text-violet-800 ring-1 ring-violet-200',
  shipped: 'bg-cyan-100 text-cyan-800 ring-1 ring-cyan-200',
  delivered: 'bg-green-100 text-green-800 ring-1 ring-green-200',
  cancelled: 'bg-red-100 text-red-800 ring-1 ring-red-200',
}

const PAYMENT_STATUS_STYLES: Record<string, string> = {
  paid: 'bg-green-100 text-green-800 ring-1 ring-green-200',
  pending: 'bg-amber-100 text-amber-800 ring-1 ring-amber-200',
  failed: 'bg-red-100 text-red-800 ring-1 ring-red-200',
  refunded: 'bg-gray-100 text-gray-700 ring-1 ring-gray-200',
  cancelled: 'bg-red-100 text-red-800 ring-1 ring-red-200',
}

const DEFAULT_BADGE = 'bg-gray-100 text-gray-700 ring-1 ring-gray-200'

function StatusBadge({ status, kind }: { status: string; kind: 'order' | 'payment' }) {
  const styles =
    kind === 'order'
      ? ORDER_STATUS_STYLES[status?.toLowerCase?.() ?? ''] ?? DEFAULT_BADGE
      : PAYMENT_STATUS_STYLES[status?.toLowerCase?.() ?? ''] ?? DEFAULT_BADGE
  return (
    <span className={`badge capitalize ${styles}`}>
      {(status || 'unknown').replace(/[_-]+/g, ' ')}
    </span>
  )
}

function SkeletonBlock({ className = '' }: { className?: string }) {
  return <div className={`shimmer rounded-xl ${className}`} />
}

function EmptyState({
  icon: Icon,
  title,
  hint,
}: {
  icon: React.ComponentType<{ className?: string }>
  title: string
  hint?: string
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center py-10 text-center">
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-gray-100">
        <Icon className="h-6 w-6 text-gray-400" />
      </div>
      <p className="text-sm font-medium text-gray-700">{title}</p>
      {hint && <p className="mt-1 text-xs text-gray-400">{hint}</p>}
    </div>
  )
}

export default function AdminDashboard() {
  const [data, setData] = useState<AdminAnalytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [redirecting, setRedirecting] = useState(false)

  useEffect(() => {
    loadAnalytics()
  }, [])

  const loadAnalytics = async () => {
    setLoading(true)
    setError(null)
    try {
      const analytics = await admin.adminAnalytics()
      setData(analytics ?? {})
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      console.error('Failed to load analytics:', message)
      if (isAuthError(message)) {
        setRedirecting(true)
        window.location.href = '/admin/login'
        return
      }
      setError(message || 'Failed to load analytics')
    } finally {
      setLoading(false)
    }
  }

  // ---------------------------------------------------- defensive extraction
  const totals = data?.totals ?? {}
  const revenue = Number(totals.revenue_total ?? 0)
  const orders = Number(totals.orders ?? 0)
  const users = Number(totals.users ?? 0)
  const products = Number(totals.products ?? 0)
  const activeProducts = totals.active_products
  const pendingOrders = Number(totals.pending_orders ?? 0)
  const lowStockCount = Number(totals.low_stock_count ?? 0)

  const revenueByDay = Array.isArray(data?.revenue_by_day) ? data!.revenue_by_day! : []
  const ordersByStatus = Array.isArray(data?.orders_by_status) ? data!.orders_by_status! : []
  const topProducts = Array.isArray(data?.top_products) ? data!.top_products! : []
  const lowStock = Array.isArray(data?.low_stock) ? data!.low_stock! : []
  const recentOrders = Array.isArray(data?.recent_orders) ? data!.recent_orders! : []

  const revenue30d = revenueByDay.reduce((sum, d) => sum + (Number(d.revenue) || 0), 0)
  const statusTotal = ordersByStatus.reduce((sum, d) => sum + (Number(d.count) || 0), 0)

  // -------------------------------------------------------------- loading
  if (loading || redirecting) {
    return (
      <div className="p-6 lg:p-8">
        <SkeletonBlock className="mb-1 h-4 w-24" />
        <SkeletonBlock className="mb-8 h-8 w-64" />
        <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonBlock key={i} className="h-32" />
          ))}
        </div>
        <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
          <SkeletonBlock className="h-80 lg:col-span-2" />
          <SkeletonBlock className="h-80" />
        </div>
        <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <SkeletonBlock className="h-72" />
          <SkeletonBlock className="h-72" />
        </div>
        <SkeletonBlock className="h-64" />
      </div>
    )
  }

  // ---------------------------------------------------------------- error
  if (error) {
    return (
      <div className="p-6 lg:p-8">
        <div className="mx-auto max-w-md rounded-xl border border-red-200 bg-red-50 p-8 text-center">
          <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-red-500" />
          <h1 className="font-semibold text-gray-900">Couldn&apos;t load analytics</h1>
          <p className="mt-1 text-sm text-gray-600">{error}</p>
          <button onClick={loadAnalytics} className="btn-primary mt-5">
            Try again
          </button>
        </div>
      </div>
    )
  }

  // -------------------------------------------------------------- stat cards
  const statCards = [
    {
      label: 'Revenue',
      value: revenue,
      format: (n: number) => fmtBDT(n),
      icon: Banknote,
      tile: 'from-blue-500 to-blue-700 shadow-blue-600/30',
      sub: 'all time',
    },
    {
      label: 'Orders',
      value: orders,
      format: (n: number) => Math.round(n).toLocaleString(),
      icon: ShoppingCart,
      tile: 'from-indigo-500 to-indigo-700 shadow-indigo-600/30',
      sub: 'all time',
    },
    {
      label: 'Customers',
      value: users,
      format: (n: number) => Math.round(n).toLocaleString(),
      icon: Users,
      tile: 'from-violet-500 to-violet-700 shadow-violet-600/30',
      sub: 'registered',
    },
    {
      label: 'Products',
      value: products,
      format: (n: number) => Math.round(n).toLocaleString(),
      icon: Package,
      tile: 'from-cyan-500 to-cyan-600 shadow-cyan-600/30',
      sub: activeProducts !== undefined ? `${Number(activeProducts)} active` : undefined,
    },
    {
      label: 'Pending Orders',
      value: pendingOrders,
      format: (n: number) => Math.round(n).toLocaleString(),
      icon: Clock,
      tile: 'from-amber-400 to-amber-600 shadow-amber-500/30',
      sub: 'awaiting action',
    },
    {
      label: 'Low Stock',
      value: lowStockCount,
      format: (n: number) => Math.round(n).toLocaleString(),
      icon: AlertTriangle,
      tile: 'from-red-500 to-red-600 shadow-red-600/30',
      sub: 'needs restock',
    },
  ]

  const maxTopRevenue = Math.max(...topProducts.map((p) => Number(p.revenue) || 0), 0)

  return (
    <div className="relative min-h-screen overflow-x-clip p-6 lg:p-8">
      {/* Atmosphere: soft brand glow behind the header */}
      <div
        aria-hidden
        className="pointer-events-none absolute -top-24 left-1/3 h-72 w-[36rem] max-w-full -translate-x-1/2 rounded-full bg-brand-radial blur-2xl"
      />

      {/* Header */}
      <FadeIn y={16} className="relative mb-8">
        <p className="text-xs font-semibold uppercase tracking-widest text-primary-600">Overview</p>
        <h1 className="mt-1 text-2xl font-bold text-gray-900">
          Dashboard <span className="gradient-text">Analytics</span>
        </h1>
        <p className="mt-1 text-sm text-gray-500">Store performance at a glance</p>
      </FadeIn>

      {/* Stat cards */}
      <Stagger className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6" gap={0.06} delay={0.05}>
        {statCards.map((card) => (
          <StaggerItem key={card.label} className="h-full" y={16}>
            <div className="glass-card group h-full p-5 transition-all duration-300 ease-out-expo hover:-translate-y-0.5 hover:shadow-glow-md">
              <div
                className={`flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br text-white shadow-md ${card.tile}`}
              >
                <card.icon className="h-5 w-5" />
              </div>
              <p className="mt-4 text-xs font-medium uppercase tracking-wide text-gray-500">
                {card.label}
              </p>
              <p className="mt-1 truncate text-2xl font-bold text-gray-900">
                <AnimatedNumber value={card.value} format={card.format} />
              </p>
              {card.sub && <p className="mt-0.5 text-xs text-gray-400">{card.sub}</p>}
            </div>
          </StaggerItem>
        ))}
      </Stagger>

      {/* Charts: revenue trend + status donut */}
      <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <FadeIn className="lg:col-span-2" y={20}>
          <div className="glass-card h-full p-5">
            <ChartCardHeader
              title="Revenue"
              hint="Daily revenue over the last 30 days"
              action={
                <span className="badge bg-primary-50 text-primary-700 ring-1 ring-primary-200">
                  {fmtBDT(revenue30d)} in 30d
                </span>
              }
            />
            {revenue30d > 0 ? (
              <RevenueAreaChart data={revenueByDay} />
            ) : (
              <EmptyState
                icon={SearchX}
                title="No orders yet"
                hint="Revenue will chart here once orders start rolling in"
              />
            )}
          </div>
        </FadeIn>

        <FadeIn y={20} delay={0.08}>
          <div className="glass-card h-full p-5">
            <ChartCardHeader title="Orders by status" hint="All-time distribution" />
            {statusTotal > 0 ? (
              <StatusDonut data={ordersByStatus} />
            ) : (
              <EmptyState
                icon={SearchX}
                title="No orders yet"
                hint="Status breakdown appears after the first order"
              />
            )}
          </div>
        </FadeIn>
      </div>

      {/* Top products + low stock */}
      <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <FadeIn y={20}>
          <div className="glass-card h-full p-5">
            <ChartCardHeader
              title="Top products"
              hint="Best sellers by units sold"
              action={
                <Link
                  href="/admin/products"
                  className="inline-flex items-center gap-1 text-xs font-medium text-primary-600 hover:text-primary-700 hover:underline underline-offset-4"
                >
                  Manage <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              }
            />
            {topProducts.length === 0 ? (
              <EmptyState icon={Package} title="No sales yet" hint="Top sellers show up here" />
            ) : (
              <ul className="divide-y divide-gray-100">
                {topProducts.slice(0, 6).map((p, i) => (
                  <li key={p.product_id ?? i} className="flex items-center gap-3 py-3">
                    <span
                      className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-xs font-bold ${
                        i < 3
                          ? 'bg-brand-gradient text-white shadow-sm'
                          : 'bg-gray-100 text-gray-500'
                      }`}
                    >
                      {i + 1}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-gray-900">{p.name}</p>
                      <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-gray-100">
                        <div
                          className="h-full rounded-full bg-brand-gradient"
                          style={{
                            width: `${maxTopRevenue > 0 ? Math.max(4, Math.round(((Number(p.revenue) || 0) / maxTopRevenue) * 100)) : 0}%`,
                          }}
                        />
                      </div>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="text-sm font-semibold text-gray-900">{fmtBDT(Number(p.revenue) || 0)}</p>
                      <p className="text-xs text-gray-400">
                        {Number(p.units_sold) || 0} unit{(Number(p.units_sold) || 0) === 1 ? '' : 's'}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </FadeIn>

        <FadeIn y={20} delay={0.08}>
          <div className="glass-card h-full p-5">
            <ChartCardHeader
              title="Low stock"
              hint={`${lowStock.length} product${lowStock.length === 1 ? '' : 's'} running low`}
              action={
                <Link
                  href="/admin/products"
                  className="inline-flex items-center gap-1 text-xs font-medium text-primary-600 hover:text-primary-700 hover:underline underline-offset-4"
                >
                  Restock <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              }
            />
            {lowStock.length === 0 ? (
              <EmptyState
                icon={CheckCircle2}
                title="All stocked up"
                hint="No products are below the low-stock threshold"
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="text-left text-xs uppercase tracking-wide text-gray-400">
                      <th className="pb-2 font-medium">Product</th>
                      <th className="pb-2 font-medium">SKU</th>
                      <th className="pb-2 text-right font-medium">Stock</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lowStock.map((p, i) => {
                      const qty = Number(p.stock_quantity) || 0
                      return (
                        <tr
                          key={p.product_id ?? i}
                          className="border-t border-red-100 bg-red-50/40 transition-colors hover:bg-red-50/80"
                        >
                          <td className="max-w-[16rem] truncate py-2.5 pl-2 pr-2 text-sm font-medium text-gray-900">
                            {p.name}
                          </td>
                          <td className="py-2.5 pr-2 font-mono text-xs text-gray-500">{p.sku || '—'}</td>
                          <td className="py-2.5 pr-2 text-right">
                            <span
                              className={`badge ${
                                qty === 0
                                  ? 'bg-red-600 text-white ring-1 ring-red-600'
                                  : 'bg-red-100 text-red-700 ring-1 ring-red-200'
                              }`}
                            >
                              {qty === 0 ? 'Out of stock' : `${qty} left`}
                            </span>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </FadeIn>
      </div>

      {/* Recent orders */}
      <FadeIn y={20}>
        <div className="glass-card p-5">
          <ChartCardHeader
            title="Recent orders"
            hint="Latest activity across the store"
            action={
              <Link
                href="/admin/orders"
                className="inline-flex items-center gap-1 text-xs font-medium text-primary-600 hover:text-primary-700 hover:underline underline-offset-4"
              >
                View all <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            }
          />
          {recentOrders.length === 0 ? (
            <EmptyState icon={ShoppingCart} title="No orders yet" hint="New orders will appear here" />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wide text-gray-400">
                    <th className="pb-2 font-medium">Order #</th>
                    <th className="pb-2 font-medium">Customer</th>
                    <th className="pb-2 font-medium">Payment</th>
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 text-right font-medium">Total</th>
                    <th className="pb-2 text-right font-medium">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {recentOrders.map((order, i) => (
                    <tr
                      key={order.id ?? i}
                      className="border-t border-gray-100 transition-colors hover:bg-white/80"
                    >
                      <td className="py-3 pr-4 font-medium">
                        <Link
                          href="/admin/orders"
                          className="text-primary-700 hover:text-primary-800 hover:underline underline-offset-4"
                        >
                          {order.order_number}
                        </Link>
                      </td>
                      <td className="max-w-[12rem] truncate py-3 pr-4 text-sm text-gray-700">
                        {order.customer || 'Guest'}
                      </td>
                      <td className="py-3 pr-4">
                        <StatusBadge status={order.payment_status} kind="payment" />
                      </td>
                      <td className="py-3 pr-4">
                        <StatusBadge status={order.order_status} kind="order" />
                      </td>
                      <td className="py-3 pr-4 text-right text-sm font-semibold text-gray-900">
                        {fmtBDT(Number(order.total_amount) || 0)}
                      </td>
                      <td className="py-3 text-right text-sm text-gray-500">
                        {order.created_at
                          ? parseUtcDate(order.created_at).toLocaleDateString(undefined, {
                              month: 'short',
                              day: 'numeric',
                            })
                          : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </FadeIn>
    </div>
  )
}
