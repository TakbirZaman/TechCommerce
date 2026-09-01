"use client";

import { useCheckoutWizard } from "@/hooks/useCheckoutWizard";
import { DeliveryStep } from "./DeliveryStep";
import { SummaryStep } from "./SummaryStep";
import { PaymentStep } from "./PaymentStep";

const STEP_LABELS = ["Delivery", "Summary", "Payment"];

export default function CheckoutPage() {
  const step = useCheckoutWizard((s) => s.step);

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">Checkout</h1>

      <div className="mb-6 flex items-center gap-2">
        {STEP_LABELS.map((label, idx) => (
          <div key={label} className="flex flex-1 items-center gap-2">
            <div
              className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-medium ${
                step === idx + 1
                  ? "bg-brand-600 text-white"
                  : step > idx + 1
                    ? "bg-brand-100 text-brand-700"
                    : "bg-gray-200 text-gray-500"
              }`}
            >
              {idx + 1}
            </div>
            <span className="text-sm text-gray-600">{label}</span>
            {idx < STEP_LABELS.length - 1 && <div className="h-px flex-1 bg-gray-200" />}
          </div>
        ))}
      </div>

      {step === 1 && <DeliveryStep />}
      {step === 2 && <SummaryStep />}
      {step === 3 && <PaymentStep />}
    </div>
  );
}
