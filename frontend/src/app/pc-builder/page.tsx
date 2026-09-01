'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { pcBuilder, catalog } from '@/lib/api'
import { Cpu, Plus, Trash2, AlertTriangle, CheckCircle, RefreshCw } from 'lucide-react'

interface Component {
  category: string
  name: string
  product_id?: number
  product_name?: string
  specs?: any
}

const defaultComponents: Component[] = [
  { category: 'cpu', name: 'Processor' },
  { category: 'motherboard', name: 'Motherboard' },
  { category: 'ram', name: 'RAM' },
  { category: 'gpu', name: 'Graphics Card' },
  { category: 'storage', name: 'Storage' },
  { category: 'psu', name: 'Power Supply' },
  { category: 'case', name: 'Case' },
]

export default function PCBuilderPage() {
  const [components, setComponents] = useState<Component[]>(defaultComponents)
  const [compatibility, setCompatibility] = useState<any>(null)
  const [checking, setChecking] = useState(false)
  const [totalPrice, setTotalPrice] = useState(0)
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [products, setProducts] = useState<any[]>([])
  const [loadingProducts, setLoadingProducts] = useState(false)

  useEffect(() => {
    checkCompatibility()
    calculateTotal()
  }, [components])

  const checkCompatibility = async () => {
    const filled = components.filter(c => c.product_id)
    if (filled.length < 2) return

    setChecking(true)
    try {
      const result = await pcBuilder.checkCompatibility(
        filled.map(c => ({ category: c.category, product_id: c.product_id! }))
      )
      setCompatibility(result)
    } catch (error) {
      console.error('Compatibility check failed:', error)
    } finally {
      setChecking(false)
    }
  }

  const calculateTotal = async () => {
    const ids = components.filter(c => c.product_id).map(c => c.product_id!)
    if (ids.length === 0) {
      setTotalPrice(0)
      return
    }
    try {
      const data = await pcBuilder.calculateTotal(ids)
      setTotalPrice(data.total_price)
    } catch (error) {
      console.error('Failed to calculate total:', error)
    }
  }

  const loadProducts = async (category: string) => {
    setSelectedCategory(category)
    setLoadingProducts(true)
    try {
      const data = await catalog.products({ category, limit: 50 })
      setProducts(data)
    } catch (error) {
      console.error('Failed to load products:', error)
    } finally {
      setLoadingProducts(false)
    }
  }

  const selectProduct = (product: any) => {
    setComponents(prev =>
      prev.map(c =>
        c.category === selectedCategory
          ? { ...c, product_id: product.id, product_name: product.name, specs: product.specifications }
          : c
      )
    )
    setSelectedCategory(null)
    setProducts([])
  }

  const removeComponent = (category: string) => {
    setComponents(prev =>
      prev.map(c =>
        c.category === category
          ? { ...c, product_id: undefined, product_name: undefined, specs: undefined }
          : c
      )
    )
  }

  const loadSuggestedComponents = async () => {
    try {
      const result = await pcBuilder.suggestedComponents(
        components.filter(c => c.product_id).map(c => ({ category: c.category, product_id: c.product_id! }))
      )
      // Update components with suggestions
      const newComponents = components.map(c => {
        if (!c.product_id && result.suggestions?.[c.category]) {
          const suggestion = result.suggestions[c.category]
          return { ...c, product_id: suggestion.id, product_name: suggestion.name }
        }
        return c
      })
      setComponents(newComponents)
    } catch (error) {
      console.error('Failed to load suggestions:', error)
    }
  }

  const handleSaveBuild = async () => {
    const filled = components.filter(c => c.product_id)
    if (filled.length === 0) {
      alert('Add at least one component to save')
      return
    }
    const name = prompt('Enter a name for this build:')
    if (!name) return
    
    try {
      await pcBuilder.create({
        name,
        components: filled.map(c => ({ category: c.category, product_id: c.product_id! })),
      })
      alert('Build saved!')
    } catch (error) {
      alert('Failed to save build')
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Cpu className="w-8 h-8" />
            PC Builder
          </h1>
          <p className="text-gray-600 mt-1">Build your perfect PC with real-time compatibility checking</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={loadSuggestedComponents}
            className="flex items-center gap-2 px-4 py-2 border rounded-lg hover:bg-gray-50"
          >
            <RefreshCw className="w-4 h-4" />
            Auto-Fill Suggestions
          </button>
          <button
            onClick={handleSaveBuild}
            className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700"
          >
            Save Build
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Components List */}
        <div className="lg:col-span-2 space-y-3">
          {components.map((comp) => (
            <div
              key={comp.category}
              className={`bg-white rounded-lg shadow-md p-4 border-l-4 ${
                comp.product_id ? 'border-green-500' : 'border-gray-300'
              }`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold">{comp.name}</h3>
                  {comp.product_name ? (
                    <p className="text-sm text-gray-600">{comp.product_name}</p>
                  ) : (
                    <p className="text-sm text-gray-400">Not selected</p>
                  )}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => loadProducts(comp.category)}
                    className="p-2 text-primary-600 hover:bg-primary-50 rounded-lg"
                  >
                    <Plus className="w-5 h-5" />
                  </button>
                  {comp.product_id && (
                    <button
                      onClick={() => removeComponent(comp.category)}
                      className="p-2 text-red-500 hover:bg-red-50 rounded-lg"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Summary & Compatibility */}
        <div className="space-y-4">
          {/* Price Summary */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-bold mb-4">Build Summary</h2>
            <div className="space-y-2 mb-4">
              {components.filter(c => c.product_name).map((c) => (
                <div key={c.category} className="flex justify-between text-sm">
                  <span className="text-gray-600 truncate flex-1">{c.product_name}</span>
                </div>
              ))}
            </div>
            <div className="border-t pt-4">
              <div className="flex justify-between text-lg font-bold">
                <span>Total</span>
                <span className="text-primary-600">৳{totalPrice.toLocaleString()}</span>
              </div>
            </div>
          </div>

          {/* Compatibility */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-bold mb-4">Compatibility Check</h2>
            {checking ? (
              <p className="text-gray-500">Checking compatibility...</p>
            ) : compatibility?.is_compatible ? (
              <div className="flex items-center gap-2 text-green-600">
                <CheckCircle className="w-5 h-5" />
                <span>All components are compatible!</span>
              </div>
            ) : compatibility?.issues?.length > 0 ? (
              <div className="space-y-2">
                {compatibility.issues.map((issue: any, index: number) => (
                  <div key={index} className="flex items-start gap-2 text-amber-600">
                    <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                    <span className="text-sm">{issue}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-sm">Add at least 2 components to check compatibility</p>
            )}
          </div>

          {/* Clear All */}
          <button
            onClick={() => setComponents(defaultComponents)}
            className="w-full py-2 text-red-600 hover:bg-red-50 rounded-lg"
          >
            Clear All Components
          </button>
        </div>
      </div>

      {/* Product Selection Modal */}
      {selectedCategory && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[80vh] overflow-hidden">
            <div className="p-4 border-b flex items-center justify-between">
              <h3 className="text-lg font-bold capitalize">Select {selectedCategory}</h3>
              <button
                onClick={() => setSelectedCategory(null)}
                className="text-gray-500 hover:text-gray-700"
              >
                ×
              </button>
            </div>
            <div className="p-4 overflow-y-auto max-h-[60vh]">
              {loadingProducts ? (
                <div className="space-y-4">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="h-16 bg-gray-100 rounded animate-pulse"></div>
                  ))}
                </div>
              ) : products.length > 0 ? (
                <div className="space-y-2">
                  {products.map((product) => (
                    <button
                      key={product.id}
                      onClick={() => selectProduct(product)}
                      className="w-full p-4 text-left border rounded-lg hover:bg-primary-50 hover:border-primary-500 flex items-center gap-4"
                    >
                      <div className="w-16 h-16 bg-gray-100 rounded flex items-center justify-center">
                        {product.images?.[0]?.url ? (
                          <img src={product.images[0].url} alt={product.name} className="w-full h-full object-cover rounded" />
                        ) : (
                          <span className="text-xl">📦</span>
                        )}
                      </div>
                      <div className="flex-1">
                        <h4 className="font-medium">{product.name}</h4>
                        <p className="text-primary-600">৳{product.price.toLocaleString()}</p>
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">No products found in this category</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
