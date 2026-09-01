import { create } from "zustand";
import type { DeliveryInfo, PaymentMethod } from "@/types/commerce";

/**
 * This store holds ONLY UI/navigation state for the checkout wizard —
 * which step the user is on, and the form values they've entered so far.
 * It never holds price/subtotal/total: those always come fresh from the
 * server (see /checkout POST response and /orders/[id] GET), so there is
 * no client-computed money value anywhere in this store to go stale or be
 * tampered with.
 */
interface CheckoutWizardState {
  step: 1 | 2 | 3;
  delivery: DeliveryInfo | null;
  paymentMethod: PaymentMethod | null;
  setStep: (step: 1 | 2 | 3) => void;
  setDelivery: (delivery: DeliveryInfo) => void;
  setPaymentMethod: (method: PaymentMethod) => void;
  reset: () => void;
}

export const useCheckoutWizard = create<CheckoutWizardState>((set) => ({
  step: 1,
  delivery: null,
  paymentMethod: null,
  setStep: (step) => set({ step }),
  setDelivery: (delivery) => set({ delivery, step: 2 }),
  setPaymentMethod: (paymentMethod) => set({ paymentMethod }),
  reset: () => set({ step: 1, delivery: null, paymentMethod: null }),
}));
