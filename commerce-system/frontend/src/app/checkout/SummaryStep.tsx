"use client";

import { useCart } from "@/hooks/useCart";
import { Button } from "@/components/ui/Button";
import { useCheckoutWizard } from "@/hooks/useCheckoutWizard";

export function SummaryStep() {
  const { data: cart, isLoading } = useCart();
  const delivery = useCheckoutWizard((s) => s.delivery);
  const setStep = useCheckoutWizard((s) => s.setStep);

  if (isLoading || !cart) return <p className="text-gray-500">Loading order summary…</p>;

  return (
    <div className="space-y-4 rounded-xl bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold">Order Summary</h2>

      <div className="divide-y divide-gray-100">
        {cart.items.map((item) => (
          <div key={item.id} className="flex justify-between py-2 text-sm">
            <span>
              {item.product_name} × {item.quantity}
            </span>
            <span>৳{item.subtotal}</span>
          </div>
        ))}
      </div>

      <div className="rounded-lg bg-gray-50 p-3 text-sm">
        <p className="font-medium text-gray-700">Deliver to</p>
        <p className="text-gray-600">
          {delivery?.full_name} · {delivery?.phone}
        </p>
        <p className="text-gray-600">
          {delivery?.address}, {delivery?.area}, {delivery?.city} {delivery?.postal_code}
        </p>
      </div>

      <div className="flex justify-between border-t border-gray-200 pt-3 text-sm text-gray-600">
        <span>Subtotal</span>
        <span>৳{cart.subtotal}</span>
      </div>
      <p className="text-xs text-gray-400">
        Final discount, delivery charge, and total are calculated by the server on the next step.
      </p>

      <div className="flex gap-3">
        <Button variant="secondary" onClick={() => setStep(1)} className="flex-1">
          Back
        </Button>
        <Button onClick={() => setStep(3)} className="flex-1">
          Continue to Payment
        </Button>
      </div>
    </div>
  );
}
