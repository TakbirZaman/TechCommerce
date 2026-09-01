"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { useCheckoutWizard } from "@/hooks/useCheckoutWizard";
import { useCheckout, useInitiatePayment } from "@/hooks/useOrders";
import type { PaymentMethod } from "@/types/commerce";

const METHODS: { id: PaymentMethod; label: string }[] = [
  { id: "BKASH", label: "bKash" },
  { id: "NAGAD", label: "Nagad" },
  { id: "SSLCOMMERZ", label: "SSLCommerz (Cards / Mobile Banking)" },
];

export function PaymentStep() {
  const router = useRouter();
  const delivery = useCheckoutWizard((s) => s.delivery);
  const setStep = useCheckoutWizard((s) => s.setStep);
  const paymentMethod = useCheckoutWizard((s) => s.paymentMethod);
  const setPaymentMethod = useCheckoutWizard((s) => s.setPaymentMethod);

  const checkout = useCheckout();
  const initiatePayment = useInitiatePayment();
  const [error, setError] = useState<string | null>(null);

  async function handlePay() {
    setError(null);
    if (!delivery || !paymentMethod) return;

    try {
      // 1. Create the order — backend recalculates every total server-side.
      const order = await checkout.mutateAsync({ delivery, payment_method: paymentMethod });

      // 2. Initiate payment with the chosen gateway for that order.
      const payment = await initiatePayment.mutateAsync(order.id);

      // 3. Real gateways require an actual redirect to their hosted payment
      //    page — we never mark the order paid client-side. The order-success
      //    page re-checks payment/order status from the backend once the
      //    gateway redirects back.
      if (payment.redirect_url) {
        window.location.href = payment.redirect_url;
      } else {
        // Some flows (e.g. after a webhook already resolved) may not need a redirect.
        router.push(`/order-success?order_id=${order.id}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    }
  }

  const isProcessing = checkout.isPending || initiatePayment.isPending;

  return (
    <div className="space-y-4 rounded-xl bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold">Choose Payment Method</h2>

      <div className="space-y-2">
        {METHODS.map((method) => (
          <label
            key={method.id}
            className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 ${
              paymentMethod === method.id ? "border-brand-600 ring-1 ring-brand-600" : "border-gray-200"
            }`}
          >
            <input
              type="radio"
              name="payment_method"
              checked={paymentMethod === method.id}
              onChange={() => setPaymentMethod(method.id)}
            />
            <span>{method.label}</span>
          </label>
        ))}
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
          {error}{" "}
          <button className="underline" onClick={handlePay}>
            Retry
          </button>
        </div>
      )}

      {isProcessing && (
        <p className="text-sm text-gray-500">
          {checkout.isPending ? "Placing your order…" : "Redirecting to payment gateway…"}
        </p>
      )}

      <div className="flex gap-3">
        <Button variant="secondary" onClick={() => setStep(2)} className="flex-1" disabled={isProcessing}>
          Back
        </Button>
        <Button onClick={handlePay} className="flex-1" disabled={!paymentMethod || isProcessing}>
          Pay Now
        </Button>
      </div>
    </div>
  );
}
