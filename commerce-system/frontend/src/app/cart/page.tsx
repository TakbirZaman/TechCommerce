"use client";

import Link from "next/link";
import { useCart, useRemoveCartItem, useUpdateCartItem, useClearCart } from "@/hooks/useCart";
import { Button } from "@/components/ui/Button";
import type { CartItem } from "@/types/commerce";

function CartRow({ item }: { item: CartItem }) {
  const updateItem = useUpdateCartItem();
  const removeItem = useRemoveCartItem();

  const atMaxStock = item.quantity >= item.available_stock;

  return (
    <div className="flex items-center gap-4 border-b border-gray-200 py-4">
      <div className="h-16 w-16 flex-shrink-0 overflow-hidden rounded-lg bg-gray-100">
        {item.product_image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={item.product_image_url} alt={item.product_name} className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-xs text-gray-400">No image</div>
        )}
      </div>

      <div className="flex-1">
        <p className="font-medium">{item.product_name}</p>
        <p className="text-sm text-gray-500">৳{item.unit_price} each</p>
        {atMaxStock && <p className="text-xs text-amber-600">Max available stock reached</p>}
      </div>

      <div className="flex items-center gap-2">
        <button
          className="h-8 w-8 rounded-md border border-gray-300 text-lg leading-none hover:bg-gray-50 disabled:opacity-40"
          disabled={item.quantity <= 1 || updateItem.isPending}
          onClick={() => updateItem.mutate({ itemId: item.id, quantity: item.quantity - 1 })}
        >
          −
        </button>
        <span className="w-6 text-center">{item.quantity}</span>
        <button
          className="h-8 w-8 rounded-md border border-gray-300 text-lg leading-none hover:bg-gray-50 disabled:opacity-40"
          disabled={atMaxStock || updateItem.isPending}
          onClick={() => updateItem.mutate({ itemId: item.id, quantity: item.quantity + 1 })}
        >
          +
        </button>
      </div>

      <div className="w-24 text-right font-medium">৳{item.subtotal}</div>

      <button
        className="text-sm text-red-600 hover:underline"
        onClick={() => removeItem.mutate(item.id)}
        disabled={removeItem.isPending}
      >
        Remove
      </button>
    </div>
  );
}

export default function CartPage() {
  const { data: cart, isLoading, isError } = useCart();
  const clearCart = useClearCart();

  if (isLoading) return <p className="text-gray-500">Loading cart…</p>;
  if (isError) return <p className="text-red-600">Could not load your cart. Please try again.</p>;
  if (!cart || cart.items.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-gray-300 p-12 text-center">
        <p className="text-gray-500">Your cart is empty.</p>
        <Link href="/" className="mt-4 inline-block text-brand-600 hover:underline">
          Continue shopping
        </Link>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Your Cart</h1>
        <button
          className="text-sm text-gray-500 hover:underline"
          onClick={() => clearCart.mutate()}
          disabled={clearCart.isPending}
        >
          Clear cart
        </button>
      </div>

      <div className="rounded-xl bg-white p-4 shadow-sm">
        {cart.items.map((item) => (
          <CartRow key={item.id} item={item} />
        ))}
      </div>

      <div className="mt-6 flex items-center justify-between rounded-xl bg-white p-4 shadow-sm">
        <div>
          <p className="text-sm text-gray-500">Subtotal ({cart.total_items} items)</p>
          <p className="text-xl font-semibold">৳{cart.subtotal}</p>
        </div>
        <Link href="/checkout">
          <Button>Proceed to Checkout</Button>
        </Link>
      </div>
      <p className="mt-2 text-xs text-gray-400">
        Delivery charge and any discounts are calculated at checkout.
      </p>
    </div>
  );
}
