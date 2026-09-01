"use client";

import { useParams } from "next/navigation";
import { useOrder, useInvoiceDownloadUrl } from "@/hooks/useOrders";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Button } from "@/components/ui/Button";

export default function OrderDetailPage() {
  const params = useParams<{ id: string }>();
  const orderId = Number(params.id);

  const { data: order, isLoading, isError } = useOrder(orderId);
  const invoiceQuery = useInvoiceDownloadUrl(orderId);

  if (isLoading) return <p className="text-gray-500">Loading order…</p>;
  // The backend scopes /orders/{id} to the authenticated user, so a 404 here
  // also covers "this order belongs to someone else" — no separate client
  // check is needed or possible.
  if (isError || !order) return <p className="text-red-600">Order not found.</p>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">{order.order_number}</h1>
        <p className="text-sm text-gray-500">{new Date(order.created_at).toLocaleString()}</p>
        <div className="mt-2 flex gap-2">
          <StatusBadge status={order.payment_status} />
          <StatusBadge status={order.order_status} />
        </div>
      </div>

      <div className="rounded-xl bg-white p-6 shadow-sm">
        <h2 className="mb-3 font-semibold">Items</h2>
        <div className="divide-y divide-gray-100">
          {order.items.map((item) => (
            <div key={item.product_id} className="flex justify-between py-2 text-sm">
              <span>
                {item.product_name} ({item.product_sku}) × {item.quantity}
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

      <div className="rounded-xl bg-white p-6 shadow-sm">
        <h2 className="mb-2 font-semibold">Delivery Address</h2>
        <p className="text-sm text-gray-600">{order.shipping_full_name}</p>
        <p className="text-sm text-gray-600">{order.shipping_phone}</p>
        <p className="text-sm text-gray-600">
          {order.shipping_address}, {order.shipping_area}, {order.shipping_city}{" "}
          {order.shipping_postal_code}
        </p>
      </div>

      {order.payment_status === "PAID" && (
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
      )}
    </div>
  );
}
