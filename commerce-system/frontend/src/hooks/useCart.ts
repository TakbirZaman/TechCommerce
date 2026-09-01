"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Cart } from "@/types/commerce";

const CART_KEY = ["cart"];

export function useCart() {
  return useQuery({
    queryKey: CART_KEY,
    queryFn: () => api.get<Cart>("/api/v1/cart"),
  });
}

export function useAddToCart() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { product_id: number; quantity: number }) =>
      api.post<Cart>("/api/v1/cart/items", input),
    onSuccess: (data) => qc.setQueryData(CART_KEY, data),
  });
}

export function useUpdateCartItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { itemId: number; quantity: number }) =>
      api.patch<Cart>(`/api/v1/cart/items/${input.itemId}`, { quantity: input.quantity }),
    onSuccess: (data) => qc.setQueryData(CART_KEY, data),
  });
}

export function useRemoveCartItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (itemId: number) => api.delete<Cart>(`/api/v1/cart/items/${itemId}`),
    onSuccess: (data) => qc.setQueryData(CART_KEY, data),
  });
}

export function useClearCart() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.delete<Cart>("/api/v1/cart"),
    onSuccess: (data) => qc.setQueryData(CART_KEY, data),
  });
}
