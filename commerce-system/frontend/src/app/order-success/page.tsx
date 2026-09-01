"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { useOrder, useInvoiceDownloadUrl } from "@/hooks/useOrders";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Button } from "@/components/ui/Button";

function OrderSuccessContent() {
  const params = useSearchParams();
  const orderId = Number(params.get("order_id"));

  // Poll while payment is still resolving — the gateway callback may land
  // a few seconds after the redirect back to this page. We never mark
  // anything paid client-side; this just re-reads backend truth until it
  // settles into PAID or FAILED.
  const { data: order, isLoading, isError } = useOrder(orderId, {
    refetchInterval: (query) => {
      const status = query.state.data?.payment_status;
      return status === "PENDING" || status === "INITIATED" ? 3000 : false;
    },
  });

  const invoiceQuery = useInvoiceDownloadUrl(orderId);

  if (!orderId) {
    return <p className="text-red-600">No order specified.</p>;
  }
  if (isLoading) return <p className="text-gray-500">Checking your order status…</p>;
  if (isError || !order) return <p className="text-red-600">Could not load this order.</p>;

  const isPaid = order.payment_status === "PAID";
  const isFailed = order.payment_status === "FAILED";

  return (
    <div className="space-y-6">
      <div
        className={`rounded-xl p-6 ${isPaid ? "bg-green-50" : isFailed ? "bg-red-50" : "bg-amber-50"}`}
      >
        <h1 className="text-xl font-semibold">
          {isPaid ? "Payment Successful" : isFailed ? "Payment Failed" : "Payment Processing"}
        </h1>
        <p className="mt-1 text-sm text-gray-600">
          Order <span className="font-medium">{order.order_number}</span>
        </p>
        <div className="mt-3 flex gap-2">
          <StatusBadge status={order.payment_status} />
          <StatusBadge status={order.order_status} />
        </div>
      </div>

      <div className="rounded-xl bg-white p-6 shadow-sm">
        <h2 className="mb-3 font-semibold">Order Details</h2>
        <div className="divide-y divide-gray-100">
          {order.items.map((item) => (
            <div key={item.product_id} className="flex justify-between py-2 text-sm">
              <span>
                {item.product_name} × {item.quantity}
              </span>
              <span>৳{item.subtotal}</span>
            </div>
          ))}
        </div>
        <div className="mt-3 space-y-1 border-t border-gray-200 pt-3 text-sm">
          <div className="flex justify-between text-gray-600">
            <span>Subtotal</span>
            <span>৳{order.subtotal}</span>
          </div>
          <div className="flex justify-between text-gray-600">
            <span>Discount</span>
            <span>-৳{order.discount}</span>
          </div>
          <div className="flex justify-between text-gray-600">
            <span>Delivery</span>
            <span>৳{order.delivery_charge}</span>
          </div>
          <div className="flex justify-between font-semibold">
            <span>Total</span>
            <span>৳{order.total_amount}</span>
          </div>
        </div>
      </div>

      {isPaid && (
        <div className="flex gap-3">
          <Button
            variant="secondary"
            onClick={async () => {
              const result = await invoiceQuery.refetch();
              if (result.data?.download_url) {
                window.open(result.data.download_url, "_blank");
              }
            }}
          >
            Download Invoice
          </Button>
          <Link href={`/orders/${order.id}`}>
            <Button variant="ghost">View Order</Button>
          </Link>
        </div>
      )}

      {isFailed && (
        <Link href="/checkout">
          <Button>Retry Payment</Button>
        </Link>
      )}
    </div>
  );
}

export default function OrderSuccessPage() {
  return (
    <Suspense fallback={<p className="text-gray-500">Loading…</p>}>
      <OrderSuccessContent />
    </Suspense>
  );
}
