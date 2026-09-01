'use client'

import { Suspense, useEffect, useRef, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { catalog, type AISearchResponse } from '@/lib/api'
import { Search as SearchIcon, Sparkles } from 'lucide-react'
import { HoverLift, Stagger, StaggerItem } from '@/components/motion'
import InterpretationChips from '@/components/search/InterpretationChips'

/**
 * Search page.
 *
 * Flow: for every query the AI search endpoint (/api/v1/catalog/ai-search) is
 * tried FIRST. If it returns results, an "AI understood" chip row, optional
 * relaxation notes and ranked results (with match score) are shown.
 * If ai-search fails, 422s (empty/missing q) or returns 0 results, we silently
 * fall back to the original normal search flow — ?q= and the navbar search box
 * behavior are unchanged.
 */

/**
 * Normalize the raw (unbounded) relevance score against the best score in the
 * current result set: the top hit reads "100% match" and the rest scale
 * proportionally, instead of everything ≥ 1.0 clamping to 100.
 */
function scoreBadgeLabel(score: number | undefined, maxScore: number): string | null {
  if (score === undefined || score === null || Number.isNaN(Number(score))) return null
  if (maxScore <= 0) return null
  const pct = Math.min(100, Math.max(0, Math.round((Number(score) / maxScore) * 100)))
  return `${pct}% match`
}

const brandLabel = (p: { brand?: any }) =>
  typeof p.brand === 'string' ? p.brand : p.brand?.name || ''

function ProductCard({
  product,
  showScore = false,
  maxScore = 0,
}: {
  product: any
  showScore?: boolean
  maxScore?: number
}) {
  const price = Number(product.price) || 0
  const compareAt = product.compare_at_price ? Number(product.compare_at_price) : null
  const badge = showScore ? scoreBadgeLabel(product.score, maxScore) : null

  return (
    <HoverLift className="h-full">
      <Link
        href={`/products/${product.slug}`}
        className="group block h-full bg-white rounded-xl shadow-sm ring-1 ring-gray-900/5 overflow-hidden transition-all duration-300 hover:ring-2 hover:ring-primary-400/60 hover:shadow-glow-md"
      >
        <div className="relative h-48 bg-gray-100 overflow-hidden flex items-center justify-center">
          {product.images?.[0]?.url ? (
            <img
              src={product.images[0].url}
              alt={product.name}
              className="h-full w-full object-cover transition-transform duration-500 ease-out-expo group-hover:scale-110"
            />
          ) : (
            <span className="text-4xl transition-transform duration-300 group-hover:scale-125 group-hover:-rotate-6">
              📦
            </span>
          )}
          {badge && (
            <span className="badge absolute right-3 top-3 bg-white/90 text-primary-700 shadow-sm ring-1 ring-primary-200 backdrop-blur">
              <Sparkles className="mr-1 h-3 w-3 text-primary-500" />
              {badge}
            </span>
          )}
        </div>
        <div className="p-4">
          <div className="text-xs font-medium uppercase tracking-wide text-gray-400 mb-1">
            {brandLabel(product)}
          </div>
          <h3 className="font-semibold text-gray-900 mb-2 line-clamp-2 group-hover:text-primary-700 transition-colors">
            {product.name}
          </h3>
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-primary-600">৳{price.toLocaleString()}</span>
            {compareAt !== null && compareAt > price && (
              <span className="text-sm text-gray-400 line-through">
                ৳{compareAt.toLocaleString()}
              </span>
            )}
          </div>
          {product.stock_quantity !== undefined && (
            <div className="mt-2 text-sm text-gray-500">
              {Number(product.stock_quantity) > 0 ? (
                <span className="inline-flex items-center gap-1.5 text-green-600">
                  <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
                  In Stock
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 text-red-600">
                  <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
                  Out of Stock
                </span>
              )}
            </div>
          )}
        </div>
      </Link>
    </HoverLift>
  )
}

function SearchPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const query = searchParams.get('q') || ''

  const [results, setResults] = useState<any[]>([])
  const [suggestions, setSuggestions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState(query)

  // AI mode state
  const [aiMode, setAiMode] = useState(false)
  const [aiData, setAiData] = useState<AISearchResponse | null>(null)

  // Stale-response guard: a monotonically increasing id per performSearch run;
  // after each await only the latest run may commit state.
  const searchIdRef = useRef(0)

  useEffect(() => {
    if (query) {
      setSearchQuery(query)
      performSearch(query)
    }
  }, [query])

  const performSearch = async (q: string) => {
    if (!q.trim()) return

    const requestId = ++searchIdRef.current

    setLoading(true)
    setAiMode(false)
    setAiData(null)

    try {
      // 1) AI search first — silently fall back on failure / 422 / 0 results.
      try {
        const ai = await catalog.aiSearch(q, 12)
        if (searchIdRef.current !== requestId) return // stale response
        const aiResults = Array.isArray(ai?.results) ? ai.results : []
        if (aiResults.length > 0) {
          setAiData(ai)
          setAiMode(true)
          setResults(aiResults)
          setSuggestions([])
          return
        }
      } catch {
        // 422 (empty query), network error, or any other failure → normal search.
      }

      // 2) Existing normal search flow (unchanged).
      const [products, autocomplete] = await Promise.all([
        catalog.search(q),
        catalog.autocomplete(q),
      ])
      if (searchIdRef.current !== requestId) return // stale response
      setResults(products)
      setSuggestions(autocomplete.products || [])
    } catch (error) {
      if (searchIdRef.current !== requestId) return // stale failure
      console.error('Search failed:', error)
    } finally {
      if (searchIdRef.current === requestId) setLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      router.push(`/search?q=${encodeURIComponent(searchQuery)}`)
    }
  }

  const resultCount = results.length

  // Best relevance score in the current result set, for proportional
  // "% match" normalization (0 → no badges shown).
  const maxScore = results.reduce((max, r) => Math.max(max, Number(r?.score) || 0), 0)

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Search Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-4">Search Products</h1>
        <form onSubmit={handleSearch}>
          <div className="relative max-w-2xl">
            <input
              type="text"
              placeholder="Search for laptops, phones, components..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-12 pr-4 py-4 text-lg border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <SearchIcon className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 w-6 h-6" />
            <button
              type="submit"
              className="absolute right-2 top-1/2 transform -translate-y-1/2 bg-primary-600 text-white px-6 py-2 rounded-lg hover:bg-primary-700"
            >
              Search
            </button>
          </div>
        </form>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Suggestions (normal-search fallback mode only) */}
        {!aiMode && suggestions.length > 0 && (
          <div className="lg:col-span-1">
            <h2 className="font-semibold mb-4">Did you mean?</h2>
            <div className="space-y-2">
              {suggestions.map((suggestion, index) => (
                <Link
                  key={index}
                  href={`/search?q=${encodeURIComponent(suggestion.text || suggestion.name)}`}
                  className="block p-3 bg-gray-50 rounded-lg hover:bg-gray-100"
                >
                  <div className="font-medium text-sm">{suggestion.text || suggestion.name}</div>
                  {suggestion.category && (
                    <div className="text-xs text-gray-500">{suggestion.category}</div>
                  )}
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Results */}
        <div className={suggestions.length > 0 && !aiMode ? 'lg:col-span-3' : 'lg:col-span-4'}>
          {query && (
            <p className="text-gray-600 mb-4">
              {loading
                ? 'Searching...'
                : `${resultCount} result${resultCount === 1 ? '' : 's'} for "${query}"`}
              {aiMode && !loading && resultCount > 0 && (
                <span className="ml-1.5 inline-flex items-center gap-1 align-middle text-xs font-medium text-primary-600">
                  <Sparkles className="h-3.5 w-3.5" />
                  ranked by relevance
                </span>
              )}
            </p>
          )}

          {/* AI interpretation (chips + relaxation notes) */}
          {aiMode && aiData?.interpretation && !loading && (
            <InterpretationChips interpretation={aiData.interpretation} />
          )}

          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="bg-white rounded-xl shadow-md p-4 overflow-hidden">
                  <div className="shimmer h-48 rounded-lg mb-4" />
                  <div className="shimmer h-4 rounded w-3/4 mb-2" />
                  <div className="shimmer h-4 rounded w-1/2" />
                </div>
              ))}
            </div>
          ) : resultCount === 0 ? (
            <div className="text-center py-12">
              <SearchIcon className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <h2 className="text-xl font-semibold mb-2">No results found</h2>
              <p className="text-gray-600 mb-4">
                Try different keywords or browse our categories
              </p>
              <div className="flex gap-4 justify-center">
                <Link href="/products" className="text-primary-600 hover:underline">
                  Browse All Products
                </Link>
                <Link href="/advisor" className="text-primary-600 hover:underline">
                  Use AI Advisor
                </Link>
              </div>
            </div>
          ) : (
            <Stagger className="grid grid-cols-1 md:grid-cols-3 gap-6" gap={0.06}>
              {results.map((product) => (
                <StaggerItem key={product.id} className="h-full">
                  <ProductCard product={product} showScore={aiMode} maxScore={maxScore} />
                </StaggerItem>
              ))}
            </Stagger>
          )}
        </div>
      </div>
    </div>
  )
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="min-h-screen" />}>
      <SearchPageContent />
    </Suspense>
  )
}
