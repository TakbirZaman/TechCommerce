"use client";

import Link from "next/link";
import { useMyOrders } from "@/hooks/useOrders";
import { StatusBadge } from "@/components/ui/StatusBadge";

export default function OrdersPage() {
  const { data: orders, isLoading, isError } = useMyOrders();

  if (isLoading) return <p className="text-gray-500">Loading your orders…</p>;
  if (isError) return <p className="text-red-600">Could not load your orders.</p>;
  if (!orders || orders.length === 0) {
    return <p className="text-gray-500">You haven&apos;t placed any orders yet.</p>;
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">Your Orders</h1>
      <div className="space-y-3">
        {orders.map((order) => (
          <Link
            key={order.id}
            href={`/orders/${order.id}`}
            className="flex items-center justify-between rounded-xl bg-white p-4 shadow-sm hover:shadow-md"
          >
            <div>
              <p className="font-medium">{order.order_number}</p>
              <div className="mt-1 flex gap-2">
                <StatusBadge status={order.payment_status} />
                <StatusBadge status={order.order_status} />
              </div>
            </div>
            <p className="font-semibold">৳{order.total_amount}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
