'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { compare } from '@/lib/api'
import { GitCompare, Trash2, ArrowLeft } from 'lucide-react'

export default function ComparePage() {
  const [items, setItems] = useState<any[]>([])
  const [comparison, setComparison] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [checking, setChecking] = useState(false)

  useEffect(() => {
    loadComparison()
  }, [])

  const loadComparison = async () => {
    try {
      const data = await compare.get()
      setItems(data.items || [])
      if (data.items?.length >= 2) {
        checkComparison()
      }
    } catch (error) {
      console.error('Failed to load comparison:', error)
    } finally {
      setLoading(false)
    }
  }

  const checkComparison = async () => {
    setChecking(true)
    try {
      const data = await compare.check()
      setComparison(data)
    } catch (error) {
      console.error('Failed to check comparison:', error)
    } finally {
      setChecking(false)
    }
  }

  const removeItem = async (itemId: number) => {
    try {
      await compare.remove(itemId)
      setItems(prev => prev.filter(item => item.id !== itemId))
      if (items.length <= 2) {
        setComparison(null)
      }
    } catch (error) {
      console.error('Failed to remove item:', error)
    }
  }

  const clearAll = async () => {
    try {
      await compare.clear()
      setItems([])
      setComparison(null)
    } catch (error) {
      console.error('Failed to clear comparison:', error)
    }
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-8"></div>
          <div className="grid grid-cols-2 gap-4">
            <div className="h-64 bg-gray-200 rounded"></div>
            <div className="h-64 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center">
        <GitCompare className="w-16 h-16 text-gray-400 mx-auto mb-4" />
        <h1 className="text-2xl font-bold mb-2">No Products to Compare</h1>
        <p className="text-gray-600 mb-6">Add products from the catalog to start comparing</p>
        <Link
          href="/products"
          className="inline-block bg-primary-600 text-white px-6 py-3 rounded-lg hover:bg-primary-700"
        >
          Browse Products
        </Link>
      </div>
    )
  }

  // Get all unique spec keys
  const allSpecKeys = [...new Set(
    items.flatMap(item => 
      item.product?.specifications?.map((s: any) => s.spec_key) || []
    )
  )]

  // Build spec lookup for each product
  const specsByProduct = items.map(item => {
    const specs: Record<string, any> = {}
    item.product?.specifications?.forEach((s: any) => {
      specs[s.spec_key] = s.value
    })
    return specs
  })

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <GitCompare className="w-8 h-8" />
            Compare Products
          </h1>
          <p className="text-gray-600 mt-1">{items.length} products selected</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={clearAll}
            className="text-red-600 hover:bg-red-50 px-4 py-2 rounded-lg"
          >
            Clear All
          </button>
          <Link
            href="/products"
            className="flex items-center gap-2 text-primary-600 hover:bg-primary-50 px-4 py-2 rounded-lg"
          >
            <ArrowLeft className="w-4 h-4" />
            Add More
          </Link>
        </div>
      </div>

      {/* Comparison Table */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="p-4 text-left bg-gray-50 font-medium text-gray-600 w-48">Feature</th>
                {items.map((item) => (
                  <th key={item.id} className="p-4 text-center min-w-[200px]">
                    <div className="relative">
                      <button
                        onClick={() => removeItem(item.id)}
                        className="absolute -top-2 -right-2 p-1 bg-red-100 text-red-600 rounded-full hover:bg-red-200"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                      <Link href={`/products/${item.product?.slug}`}>
                        <div className="w-20 h-20 bg-gray-100 rounded-lg mx-auto mb-2 flex items-center justify-center">
                          {item.product?.images?.[0]?.url ? (
                            <img src={item.product.images[0].url} alt={item.product.name} className="w-full h-full object-cover rounded-lg" />
                          ) : (
                            <span className="text-2xl">📦</span>
                          )}
                        </div>
                        <h3 className="font-semibold text-sm line-clamp-2">{item.product?.name}</h3>
                        <p className="text-primary-600 font-medium mt-1">
                          ৳{item.product?.price.toLocaleString()}
                        </p>
                      </Link>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {/* Price */}
              <tr className="border-b bg-gray-50">
                <td className="p-4 font-medium">Price</td>
                {items.map((item) => (
                  <td key={item.id} className="p-4 text-center font-bold text-primary-600">
                    ৳{item.product?.price.toLocaleString()}
                  </td>
                ))}
              </tr>

              {/* Brand */}
              <tr className="border-b">
                <td className="p-4 font-medium">Brand</td>
                {items.map((item) => (
                  <td key={item.id} className="p-4 text-center">
                    {item.product?.brand?.name || '-'}
                  </td>
                ))}
              </tr>

              {/* Category */}
              <tr className="border-b bg-gray-50">
                <td className="p-4 font-medium">Category</td>
                {items.map((item) => (
                  <td key={item.id} className="p-4 text-center">
                    {item.product?.category?.name || '-'}
                  </td>
                ))}
              </tr>

              {/* Stock */}
              <tr className="border-b">
                <td className="p-4 font-medium">Availability</td>
                {items.map((item) => (
                  <td key={item.id} className="p-4 text-center">
                    {item.product?.stock_quantity > 0 ? (
                      <span className="text-green-600">In Stock</span>
                    ) : (
                      <span className="text-red-600">Out of Stock</span>
                    )}
                  </td>
                ))}
              </tr>

              {/* Specifications */}
              {allSpecKeys.map((specKey, index) => (
                <tr key={specKey} className={`border-b ${index % 2 === 0 ? 'bg-gray-50' : ''}`}>
                  <td className="p-4 font-medium capitalize">{specKey.replace(/_/g, ' ')}</td>
                  {items.map((item, i) => (
                    <td key={item.id} className="p-4 text-center">
                      {specsByProduct[i][specKey] || '-'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Compatibility Info */}
      {checking && (
        <div className="mt-4 text-center text-gray-500">Checking compatibility...</div>
      )}
      {comparison && !comparison.is_compatible && (
        <div className="mt-4 bg-amber-50 border border-amber-200 rounded-lg p-4">
          <h3 className="font-semibold text-amber-800 mb-2">Compatibility Notes</h3>
          <ul className="list-disc list-inside text-amber-700 text-sm">
            {comparison.issues?.map((issue: string, index: number) => (
              <li key={index}>{issue}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
