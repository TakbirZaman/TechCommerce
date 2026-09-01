import { create } from "zustand";

/**
 * Section 9-11: tracks which products the user has selected to compare.
 * Kept in Zustand (client-only, ephemeral) rather than the URL since the
 * comparison tray is a cross-page selection, not a single page's filter
 * state (that part uses the URL, per Section 8).
 */
interface ComparisonState {
  productIds: number[];
  categoryId: number | null;
  maxItems: number;
  add: (productId: number, categoryId: number) => { ok: boolean; reason?: string };
  remove: (productId: number) => void;
  clear: () => void;
}

export const useComparisonStore = create<ComparisonState>((set, get) => ({
  productIds: [],
  categoryId: null,
  maxItems: 4,

  add: (productId, categoryId) => {
    const { productIds, categoryId: currentCategory, maxItems } = get();
    if (productIds.includes(productId)) return { ok: true };

    // Section 10: client-side guard mirrors the backend's compatibility
    // rule so the user gets instant feedback; the backend still validates.
    if (currentCategory !== null && currentCategory !== categoryId) {
      return { ok: false, reason: "You can only compare products of the same type." };
    }
    if (productIds.length >= maxItems) {
      return { ok: false, reason: `You can compare up to ${maxItems} products at a time.` };
    }

    set({ productIds: [...productIds, productId], categoryId });
    return { ok: true };
  },

  remove: (productId) => {
    const remaining = get().productIds.filter((id) => id !== productId);
    set({ productIds: remaining, categoryId: remaining.length ? get().categoryId : null });
  },

  clear: () => set({ productIds: [], categoryId: null }),
}));
