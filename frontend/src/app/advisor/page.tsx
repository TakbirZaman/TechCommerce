'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { advisor, assetUrl } from '@/lib/api'
import { Send, Sparkles, TrendingUp, RefreshCw } from 'lucide-react'

export default function AdvisorPage() {
  const [query, setQuery] = useState('')
  const [recommendations, setRecommendations] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [trending, setTrending] = useState<any[]>([])
  const [initialLoading, setInitialLoading] = useState(true)

  useEffect(() => {
    loadTrending()
  }, [])

  const loadTrending = async () => {
    try {
      const data = await advisor.trending(6)
      setTrending(data)
    } catch (error) {
      console.error('Failed to load trending:', error)
    } finally {
      setInitialLoading(false)
    }
  }

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return
    
    setLoading(true)
    try {
      const data = await advisor.recommend(query)
      setRecommendations(data)
    } catch (error) {
      console.error('Failed to get recommendations:', error)
    } finally {
      setLoading(false)
    }
  }

  const exampleQueries = [
    "I need a laptop under 80k for programming",
    "Suggest a phone with good camera under 30k",
    "Best gaming monitor under 40k",
    "Components for a PC build under 100k",
    "What's a good laptop for students?",
  ]

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-primary-100 text-primary-700 rounded-full mb-4">
          <Sparkles className="w-5 h-5" />
          <span className="font-medium">AI-Powered Recommendations</span>
        </div>
        <h1 className="text-3xl font-bold mb-2">AI Product Advisor</h1>
        <p className="text-gray-600">Tell us what you need, and our AI will find the perfect product for you</p>
      </div>

      {/* Chat Interface */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="bg-primary-600 text-white p-4">
          <h2 className="font-semibold">What are you looking for?</h2>
          <p className="text-primary-100 text-sm">Be specific about your budget, use case, and preferences</p>
        </div>
        
        <div className="p-4">
          <form onSubmit={handleSearch}>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="e.g., Suggest a laptop under 100k for programming"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="flex-1 px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="bg-primary-600 text-white px-6 py-3 rounded-lg hover:bg-primary-700 disabled:opacity-50 flex items-center gap-2"
              >
                <Send className="w-5 h-5" />
                {loading ? 'Thinking...' : 'Ask'}
              </button>
            </div>
          </form>

          {/* Example Queries */}
          <div className="mt-4 flex flex-wrap gap-2">
            <span className="text-sm text-gray-500">Try:</span>
            {exampleQueries.map((example, index) => (
              <button
                key={index}
                onClick={() => setQuery(example)}
                className="text-sm text-primary-600 hover:text-primary-700 hover:underline"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <div className="mt-8">
          <h2 className="text-xl font-bold mb-4">Recommended Products</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {recommendations.map((rec) => (
              <Link
                key={rec.product_id}
                href={`/products/${rec.product_slug}`}
                className="bg-white rounded-lg shadow-md p-4 hover:shadow-lg transition-shadow"
              >
                <div className="flex gap-4">
                  <div className="w-20 h-20 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    {rec.product_image ? (
                      <img src={rec.product_image} alt={rec.product_name} className="w-full h-full object-cover rounded-lg" />
                    ) : (
                      <span className="text-2xl">📦</span>
                    )}
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900">{rec.product_name}</h3>
                    <p className="text-primary-600 font-medium">৳{rec.price.toLocaleString()}</p>
                    {rec.score && (
                      <div className="mt-2 flex items-center gap-2">
                        <div className="h-2 flex-1 bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary-500"
                            style={{ width: `${rec.score * 100}%` }}
                          />
                        </div>
                        <span className="text-sm text-gray-600">{(rec.score * 100).toFixed(0)}% match</span>
                      </div>
                    )}
                    {rec.reason && (
                      <p className="text-sm text-gray-500 mt-1">{rec.reason}</p>
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Trending Products */}
      <div className="mt-12">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            Trending Products
          </h2>
          <button
            onClick={loadTrending}
            className="text-primary-600 hover:text-primary-700 flex items-center gap-1"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
        
        {initialLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="bg-white rounded-lg shadow-md p-4 animate-pulse">
                <div className="h-24 bg-gray-200 rounded mb-4"></div>
                <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                <div className="h-4 bg-gray-200 rounded w-1/2"></div>
              </div>
            ))}
          </div>
        ) : trending.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {trending.map((product) => (
              <Link
                key={product.id}
                href={`/products/${product.slug}`}
                className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow"
              >
                <div className="h-32 bg-gray-100 flex items-center justify-center">
                  {product.images?.[0]?.url ? (
                    <img src={assetUrl(product.images[0].url)} alt={product.name} className="h-full w-full object-cover" />
                  ) : (
                    <span className="text-3xl">📦</span>
                  )}
                </div>
                <div className="p-3">
                  <h3 className="font-medium text-gray-900 text-sm line-clamp-1">{product.name}</h3>
                  <p className="text-primary-600 font-medium text-sm">৳{product.price.toLocaleString()}</p>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-gray-500 text-center py-8">No trending products available</p>
        )}
      </div>
    </div>
  )
}
