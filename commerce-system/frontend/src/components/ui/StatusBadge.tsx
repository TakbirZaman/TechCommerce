import { clsx } from "clsx";
import type { OrderStatus, PaymentStatus } from "@/types/commerce";

const STATUS_STYLES: Record<string, string> = {
  PENDING: "bg-gray-100 text-gray-700",
  PAYMENT_PENDING: "bg-amber-100 text-amber-700",
  PAID: "bg-green-100 text-green-700",
  PROCESSING: "bg-blue-100 text-blue-700",
  SHIPPED: "bg-indigo-100 text-indigo-700",
  DELIVERED: "bg-green-100 text-green-800",
  CANCELLED: "bg-red-100 text-red-700",
  REFUND_REQUESTED: "bg-orange-100 text-orange-700",
  REFUNDED: "bg-purple-100 text-purple-700",
  UNPAID: "bg-gray-100 text-gray-700",
  INITIATED: "bg-amber-100 text-amber-700",
  FAILED: "bg-red-100 text-red-700",
};

export function StatusBadge({ status }: { status: OrderStatus | PaymentStatus }) {
  return (
    <span
      className={clsx(
        "inline-block rounded-full px-2.5 py-0.5 text-xs font-medium",
        STATUS_STYLES[status] ?? "bg-gray-100 text-gray-700"
      )}
    >
      {status.replaceAll("_", " ")}
    </span>
  );
}
