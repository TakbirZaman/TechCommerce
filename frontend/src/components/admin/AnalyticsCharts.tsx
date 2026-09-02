'use client'

import type { ReactNode } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

/**
 * Admin analytics charts (recharts).
 * Styled to the storefront design language: primary-blue line, gradient fill,
 * soft gray grid, glass-card tooltips. Professional, not gaudy.
 */

interface RevenuePoint {
  date: string
  revenue: number
  orders: number
}

const fmtBDT = (n: number) => `৳${Math.round(n).toLocaleString()}`
const fmtBDTCompact = (n: number) => {
  if (Math.abs(n) >= 1_000_000) return `৳${(n / 1_000_000).toFixed(1)}M`
  if (Math.abs(n) >= 1_000) return `৳${(n / 1_000).toFixed(0)}k`
  return `৳${Math.round(n)}`
}

const MONTHS_SHORT = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
]

// Revenue dates are date-only ISO strings ("2026-09-01"). Format them straight
// from their parts — no Date round-trip, so UTC parsing can never shift the
// displayed day west of UTC. Used for both x-axis ticks and the tooltip label.
const shortDate = (iso: string) => {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso ?? ''))
  if (!m) return iso
  const month = MONTHS_SHORT[Number(m[2]) - 1]
  if (!month) return iso
  return `${month} ${m[3]}`
}

interface TooltipPayloadItem {
  // recharts' ValueType/NameType unions are wider than what we render;
  // we only consume `payload`, so keep the rest loose for type compatibility.
  value?: any
  dataKey?: any
  payload?: RevenuePoint
}

/** Recharts injects a readonly payload; keep our render-prop signature compatible. */
interface TooltipRenderProps {
  active?: boolean
  payload?: readonly TooltipPayloadItem[]
}

function RevenueTooltip({ active, payload }: TooltipRenderProps) {
  if (!active || !payload?.length) return null
  const point = payload[0]?.payload
  if (!point) return null
  return (
    <div className="glass-card px-3.5 py-2.5 text-sm shadow-glow-sm">
      <p className="font-medium text-gray-900">{shortDate(point.date)}</p>
      <p className="mt-0.5 font-semibold text-primary-700">{fmtBDT(point.revenue)}</p>
      <p className="text-xs text-gray-500">{point.orders} order{point.orders === 1 ? '' : 's'}</p>
    </div>
  )
}

export function RevenueAreaChart({ data }: { data: RevenuePoint[] }) {
  const tickInterval = Math.max(0, Math.floor(data.length / 6) - 1)

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="revenueFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.32} />
              <stop offset="55%" stopColor="#3b82f6" stopOpacity={0.1} />
              <stop offset="100%" stopColor="#3b82f6" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
          <XAxis
            dataKey="date"
            tickFormatter={shortDate}
            tick={{ fontSize: 11, fill: '#6b7280' }}
            tickLine={false}
            axisLine={false}
            interval={tickInterval}
            dy={6}
          />
          <YAxis
            tickFormatter={fmtBDTCompact}
            tick={{ fontSize: 11, fill: '#6b7280' }}
            tickLine={false}
            axisLine={false}
            width={56}
          />
          <Tooltip content={<RevenueTooltip />} cursor={{ stroke: '#93c5fd', strokeWidth: 1 }} />          <Area
            type="monotone"
            dataKey="revenue"
            stroke="#2563eb"
            strokeWidth={2.5}
            fill="url(#revenueFill)"
            dot={false}
            activeDot={{ r: 5, fill: '#2563eb', stroke: '#ffffff', strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

// ---------------------------------------------------------------- Donut chart

interface StatusPoint {
  status: string
  count: number
}

const STATUS_COLORS: Record<string, string> = {
  pending: '#f59e0b',
  confirmed: '#3b82f6',
  processing: '#8b5cf6',
  shipped: '#06b6d4',
  delivered: '#10b981',
  cancelled: '#ef4444',
}

const statusColor = (status: string) => STATUS_COLORS[status?.toLowerCase?.() ?? ''] ?? '#94a3b8'

const titleCase = (s: string) =>
  (s || '').replace(/[_-]+/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

export function StatusDonut({ data }: { data: StatusPoint[] }) {
  const total = data.reduce((sum, d) => sum + (d.count || 0), 0)

  return (
    <div className="flex h-72 w-full flex-col">
      <div className="relative flex-1">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="count"
              nameKey="status"
              innerRadius="64%"
              outerRadius="88%"
              paddingAngle={3}
              cornerRadius={6}
              strokeWidth={0}
            >
              {data.map((entry) => (
                <Cell key={entry.status} fill={statusColor(entry.status)} />
              ))}
            </Pie>
            <Tooltip
              content={({ active, payload }: TooltipRenderProps) => {
                if (!active || !payload?.length) return null
                const point = payload[0]?.payload as StatusPoint | undefined
                if (!point) return null
                return (
                  <div className="glass-card px-3 py-1.5 text-xs shadow-glow-sm">
                    <span className="font-medium text-gray-900">{titleCase(point.status)}</span>
                    <span className="ml-2 text-gray-500">
                      {point.count} ({total ? Math.round((point.count / total) * 100) : 0}%)
                    </span>
                  </div>
                )
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        {/* Center label */}
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold text-gray-900">{total.toLocaleString()}</span>
          <span className="text-xs uppercase tracking-wide text-gray-400">orders</span>
        </div>
      </div>
      {/* Legend */}
      <div className="mt-2 flex flex-wrap justify-center gap-x-4 gap-y-1.5">
        {data.map((entry) => (
          <span key={entry.status} className="inline-flex items-center gap-1.5 text-xs text-gray-600">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: statusColor(entry.status) }} />
            {titleCase(entry.status)} · {entry.count}
          </span>
        ))}
      </div>
    </div>
  )
}

/** Small shared wrapper giving chart cards a consistent header. */
export function ChartCardHeader({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="mb-4 flex items-start justify-between gap-4">
      <div>
        <h2 className="font-semibold text-gray-900">{title}</h2>
        {hint && <p className="mt-0.5 text-xs text-gray-500">{hint}</p>}
      </div>
      {action}
    </div>
  )
}
