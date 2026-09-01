"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  DeliveryInfo,
  Order,
  OrderSummary,
  PaymentInitiateResponse,
  PaymentMethod,
} from "@/types/commerce";

export function useCheckout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { delivery: DeliveryInfo; payment_method: PaymentMethod }) =>
      api.post<Order>("/api/v1/checkout", input),
    onSuccess: () => {
      // cart is cleared server-side on successful checkout; drop the stale cached cart
      qc.invalidateQueries({ queryKey: ["cart"] });
    },
  });
}

export function useInitiatePayment() {
  return useMutation({
    mutationFn: (orderId: number) =>
      api.post<PaymentInitiateResponse>("/api/v1/payments/initiate", { order_id: orderId }),
  });
}

export function useMyOrders() {
  return useQuery({
    queryKey: ["orders"],
    queryFn: () => api.get<OrderSummary[]>("/api/v1/orders"),
  });
}

export function useOrder(orderId: number, options?: { refetchInterval?: number }) {
  return useQuery({
    queryKey: ["orders", orderId],
    queryFn: () => api.get<Order>(`/api/v1/orders/${orderId}`),
    enabled: Number.isFinite(orderId),
    refetchInterval: options?.refetchInterval,
  });
}

export function useInvoiceDownloadUrl(orderId: number) {
  return useQuery({
    queryKey: ["orders", orderId, "invoice"],
    queryFn: () =>
      api.get<{ invoice_number: string; download_url: string }>(
        `/api/v1/orders/${orderId}/invoice`
      ),
    enabled: false, // fetched on demand when the user clicks "download"
    retry: false,
  });
}
