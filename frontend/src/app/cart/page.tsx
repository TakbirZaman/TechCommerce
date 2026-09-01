'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { commerce } from '@/lib/api'
import { Trash2, Plus, Minus, ShoppingBag, ArrowRight, ShoppingCart } from 'lucide-react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { FadeIn } from '@/components/motion'

const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1]

export default function CartPage() {
  const [cart, setCart] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const reduceMotion = useReducedMotion()

  useEffect(() => {
    loadCart()
  }, [])

  const loadCart = async () => {
    try {
      const data = await commerce.cart()
      setCart(data)
    } catch (error) {
      console.error('Failed to load cart:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleUpdateQuantity = async (itemId: number, quantity: number) => {
    try {
      const data = await commerce.updateCartItem(itemId, quantity)
      setCart(data)
    } catch (error) {
      console.error('Failed to update quantity:', error)
    }
  }

  const handleRemoveItem = async (itemId: number) => {
    try {
      const data = await commerce.removeFromCart(itemId)
      setCart(data)
    } catch (error) {
      console.error('Failed to remove item:', error)
    }
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="space-y-4">
          <div className="h-8 shimmer rounded w-1/4" />
          <div className="h-32 shimmer rounded-xl" />
          <div className="h-32 shimmer rounded-xl" />
        </div>
      </div>
    )
  }

  if (!cart || cart.items.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center">
        <FadeIn>
          <motion.div
            animate={reduceMotion ? undefined : { y: [0, -10, 0] }}
            transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
            className="w-24 h-24 rounded-full bg-primary-50 ring-1 ring-primary-100 flex items-center justify-center mx-auto mb-6"
          >
            <ShoppingBag className="w-10 h-10 text-primary-400" />
          </motion.div>
          <h1 className="text-2xl font-bold mb-2">Your Cart is Empty</h1>
          <p className="text-gray-600 mb-6">Add some products to get started</p>
          <Link href="/products" className="btn-primary inline-flex items-center gap-2 px-6 py-3">
            Browse Products
            <ArrowRight className="w-4 h-4" />
          </Link>
        </FadeIn>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <FadeIn y={14}>
        <h1 className="text-3xl font-bold mb-8 flex items-center gap-3 text-gray-900">
          <ShoppingCart className="w-7 h-7 text-primary-600" />
          Shopping Cart
        </h1>
      </FadeIn>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Cart Items */}
        <div className="lg:col-span-2 space-y-4">
          <AnimatePresence initial={false}>
            {cart.items.map((item: any) => (
              <motion.div
                key={item.id}
                layout
                initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 16 }}
                animate={reduceMotion ? { opacity: 1 } : { opacity: 1, y: 0 }}
                exit={reduceMotion ? { opacity: 0 } : { opacity: 0, x: -48, scale: 0.95, transition: { duration: 0.25, ease: EASE } }}
                transition={{ duration: 0.35, ease: EASE }}
                className="card p-4 flex gap-4 hover:shadow-glow-sm transition-shadow duration-300"
              >
                <div className="w-24 h-24 bg-gray-100 rounded-lg flex-shrink-0 flex items-center justify-center overflow-hidden">
                  {item.product_image ? (
                    <img
                      src={item.product_image}
                      alt={item.product_name}
                      className="w-full h-full object-cover rounded-lg"
                    />
                  ) : (
                    <span className="text-2xl">📦</span>
                  )}
                </div>
                
                <div className="flex-1">
                  <Link
                    href={`/products/${item.product_id}`}
                    className="font-semibold text-gray-900 hover:text-primary-600 transition-colors"
                  >
                    {item.product_name}
                  </Link>
                  <p className="text-primary-600 font-medium mt-1">৳{item.unit_price.toLocaleString()}</p>
                  
                  <div className="flex items-center justify-between mt-4">
                    <div className="flex items-center border border-gray-300 rounded-lg overflow-hidden">
                      <motion.button
                        onClick={() => handleUpdateQuantity(item.id, item.quantity - 1)}
                        whileTap={reduceMotion ? undefined : { scale: 0.85 }}
                        className="px-3 py-1.5 hover:bg-gray-100 disabled:opacity-40 transition-colors"
                        disabled={item.quantity <= 1}
                      >
                        <Minus className="w-4 h-4 text-gray-600" />
                      </motion.button>
                      <motion.span
                        key={item.quantity}
                        initial={reduceMotion ? undefined : { scale: 1.25, color: '#2563eb' }}
                        animate={reduceMotion ? undefined : { scale: 1, color: '#1a1a1a' }}
                        transition={{ duration: 0.25 }}
                        className="px-4 py-1.5 font-semibold"
                      >
                        {item.quantity}
                      </motion.span>
                      <motion.button
                        onClick={() => handleUpdateQuantity(item.id, item.quantity + 1)}
                        whileTap={reduceMotion ? undefined : { scale: 0.85 }}
                        className="px-3 py-1.5 hover:bg-gray-100 transition-colors"
                      >
                        <Plus className="w-4 h-4 text-gray-600" />
                      </motion.button>
                    </div>
                    
                    <div className="flex items-center gap-4">
                      <motion.span
                        key={item.subtotal}
                        initial={reduceMotion ? undefined : { opacity: 0.4 }}
                        animate={reduceMotion ? undefined : { opacity: 1 }}
                        className="font-semibold"
                      >
                        ৳{item.subtotal.toLocaleString()}
                      </motion.span>
                      <motion.button
                        onClick={() => handleRemoveItem(item.id)}
                        whileTap={reduceMotion ? undefined : { scale: 0.85, rotate: -12 }}
                        whileHover={reduceMotion ? undefined : { scale: 1.15 }}
                        className="text-red-500 hover:text-red-700 transition-colors p-1 rounded-md hover:bg-red-50"
                        aria-label={`Remove ${item.product_name} from cart`}
                      >
                        <Trash2 className="w-5 h-5" />
                      </motion.button>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>

        {/* Order Summary */}
        <FadeIn y={20} delay={0.1}>
          <div className="lg:sticky lg:top-24">
            <div className="relative rounded-xl p-[1px] bg-gradient-to-br from-primary-200 via-white to-purple-200 shadow-lg shadow-gray-900/5">
              <div className="rounded-[calc(0.75rem-1px)] bg-white p-6">
                <motion.h2
                  initial={reduceMotion ? undefined : { opacity: 0, x: 12 }}
                  animate={reduceMotion ? undefined : { opacity: 1, x: 0 }}
                  transition={{ duration: 0.4, delay: 0.2, ease: EASE }}
                  className="text-xl font-bold mb-4 text-gray-900"
                >
                  Order Summary
                </motion.h2>
                
                <div className="space-y-3 mb-6">
                  <motion.div
                    key={cart.total_items}
                    initial={reduceMotion ? undefined : { opacity: 0.5, y: 4 }}
                    animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
                    className="flex justify-between text-sm"
                  >
                    <span className="text-gray-600">Subtotal ({cart.total_items} items)</span>
                    <span className="font-medium">৳{cart.subtotal.toLocaleString()}</span>
                  </motion.div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Shipping</span>
                    <span className="font-medium text-gray-500">Calculated at checkout</span>
                  </div>
                </div>

                <div className="border-t border-dashed border-gray-200 pt-4 mb-6">
                  <motion.div
                    key={cart.subtotal}
                    initial={reduceMotion ? undefined : { scale: 1.04, color: '#2563eb' }}
                    animate={reduceMotion ? undefined : { scale: 1, color: '#1d4ed8' }}
                    transition={{ duration: 0.35, ease: EASE }}
                    className="flex justify-between text-lg font-bold"
                  >
                    <span className="text-gray-900">Total</span>
                    <span>৳{cart.subtotal.toLocaleString()}</span>
                  </motion.div>
                </div>

                <motion.div
                  whileHover={reduceMotion ? undefined : { scale: 1.02 }}
                  whileTap={reduceMotion ? undefined : { scale: 0.98 }}
                  transition={{ duration: 0.15 }}
                >
                  <Link
                    href="/checkout"
                    className="w-full bg-gradient-to-br from-primary-500 to-primary-700 text-white py-3 px-6 rounded-lg font-semibold shadow-lg shadow-primary-600/30 hover:shadow-glow-md transition-shadow duration-300 flex items-center justify-center gap-2"
                  >
                    Proceed to Checkout
                    <ArrowRight className="w-5 h-5" />
                  </Link>
                </motion.div>

                <Link
                  href="/products"
                  className="w-full mt-4 text-primary-600 py-3 px-6 rounded-lg font-medium hover:bg-primary-50 flex items-center justify-center transition-colors"
                >
                  Continue Shopping
                </Link>
              </div>
            </div>
          </div>
        </FadeIn>
      </div>
    </div>
  )
}
