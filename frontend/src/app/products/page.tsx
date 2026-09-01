'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { catalog } from '@/lib/api'
import { Filter, ChevronDown, PackageSearch, SlidersHorizontal } from 'lucide-react'
import { AnimatePresence, motion } from 'framer-motion'
import { FadeIn, Stagger, StaggerItem } from '@/components/motion'

export default function ProductsPage() {
  const searchParams = useSearchParams()
  const [products, setProducts] = useState<any[]>([])
  const [brands, setBrands] = useState<any[]>([])
  const [categories, setCategories] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({
    category: searchParams.get('category') || '',
    brand: searchParams.get('brand') || '',
    min_price: searchParams.get('min_price') || '',
    max_price: searchParams.get('max_price') || '',
    sort: searchParams.get('sort') || 'popularity',
  })
  const [showFilters, setShowFilters] = useState(false)

  useEffect(() => {
    loadData()
  }, [filters])

  const loadData = async () => {
    setLoading(true)
    try {
      const [productsData, brandsData, categoriesData] = await Promise.all([
        catalog.products({
          category: filters.category || undefined,
          brand: filters.brand || undefined,
          min_price: filters.min_price ? Number(filters.min_price) : undefined,
          max_price: filters.max_price ? Number(filters.max_price) : undefined,
          sort: filters.sort,
        }),
        catalog.brands(),
        catalog.categories(),
      ])
      setProducts(productsData)
      setBrands(brandsData)
      setCategories(categoriesData)
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleFilterChange = (key: string, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }

  const filterOptionClass = (active: boolean) =>
    `block w-full text-left px-3 py-2 rounded-lg text-sm transition-colors duration-150 ${
      active
        ? 'bg-primary-100 text-primary-700 font-medium shadow-sm shadow-primary-600/10'
        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
    }`

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <FadeIn y={16}>
        <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              {filters.category ? `${filters.category.charAt(0).toUpperCase() + filters.category.slice(1)}s` : 'All Products'}
            </h1>
            <p className="mt-1 text-gray-600">{loading ? 'Loading…' : `${products.length} products found`}</p>
          </div>
          
          <div className="flex items-center gap-3 mt-4 md:mt-0">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium transition-all duration-200 active:scale-95 ${
                showFilters
                  ? 'bg-primary-50 border-primary-300 text-primary-700 shadow-sm shadow-primary-600/10'
                  : 'border-gray-300 text-gray-700 hover:bg-gray-50 hover:border-gray-400'
              }`}
            >
              <SlidersHorizontal className="w-4 h-4" />
              Filters
            </button>
            
            <div className="relative">
              <select
                value={filters.sort}
                onChange={(e) => handleFilterChange('sort', e.target.value)}
                className="appearance-none pl-4 pr-10 py-2 rounded-lg border border-gray-300 bg-white text-sm text-gray-700 cursor-pointer transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/60 focus:border-primary-500 hover:border-gray-400"
              >
                <option value="popularity">Most Popular</option>
                <option value="price_asc">Price: Low to High</option>
                <option value="price_desc">Price: High to Low</option>
                <option value="newest">Newest First</option>
                <option value="name">Name A-Z</option>
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            </div>
          </div>
        </div>
      </FadeIn>

      <div className="flex gap-8">
        {/* Filters Sidebar */}
        <AnimatePresence initial={false}>
          {showFilters && (
            <motion.div
              key="filters-sidebar"
              initial={{ opacity: 0, x: -24 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -24 }}
              transition={{ duration: 0.25, ease: 'easeOut' }}
              className="w-64 flex-shrink-0"
            >
              <div className="card sticky top-24">
                <h3 className="font-semibold mb-4 flex items-center gap-2 text-gray-900">
                  <Filter className="w-4 h-4 text-primary-600" />
                  Categories
                </h3>
                <div className="space-y-1">
                  <button
                    onClick={() => handleFilterChange('category', '')}
                    className={filterOptionClass(!filters.category)}
                  >
                    All Categories
                  </button>
                  {categories.map((cat) => (
                    <button
                      key={cat.id}
                      onClick={() => handleFilterChange('category', cat.slug)}
                      className={filterOptionClass(filters.category === cat.slug)}
                    >
                      {cat.name}
                    </button>
                  ))}
                </div>

                <h3 className="font-semibold mt-6 mb-4 text-gray-900">Brands</h3>
                <div className="space-y-1">
                  <button
                    onClick={() => handleFilterChange('brand', '')}
                    className={filterOptionClass(!filters.brand)}
                  >
                    All Brands
                  </button>
                  {brands.map((brand) => (
                    <button
                      key={brand.id}
                      onClick={() => handleFilterChange('brand', brand.slug)}
                      className={filterOptionClass(filters.brand === brand.slug)}
                    >
                      {brand.name}
                    </button>
                  ))}
                </div>

                <h3 className="font-semibold mt-6 mb-4 text-gray-900">Price Range</h3>
                <div className="flex gap-2">
                  <input
                    type="number"
                    placeholder="Min"
                    value={filters.min_price}
                    onChange={(e) => handleFilterChange('min_price', e.target.value)}
                    className="w-1/2 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/60 focus:border-primary-500"
                  />
                  <input
                    type="number"
                    placeholder="Max"
                    value={filters.max_price}
                    onChange={(e) => handleFilterChange('max_price', e.target.value)}
                    className="w-1/2 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/60 focus:border-primary-500"
                  />
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Products Grid */}
        <div className="flex-1">
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="bg-white rounded-xl shadow-sm ring-1 ring-gray-900/5 p-4 overflow-hidden">
                  <div className="h-48 shimmer rounded-lg mb-4" />
                  <div className="h-4 shimmer rounded w-3/4 mb-2" />
                  <div className="h-4 shimmer rounded w-1/2" />
                </div>
              ))}
            </div>
          ) : products.length === 0 ? (
            <FadeIn className="text-center py-16">
              <PackageSearch className="w-14 h-14 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500 text-lg">No products found</p>
              <button
                onClick={() => setFilters({ category: '', brand: '', min_price: '', max_price: '', sort: 'popularity' })}
                className="mt-4 text-primary-600 hover:text-primary-700 font-medium hover:underline underline-offset-4"
              >
                Clear filters
              </button>
            </FadeIn>
          ) : (
            <Stagger className="grid grid-cols-1 md:grid-cols-3 gap-6" gap={0.07}>
              {products.map((product) => (
                <StaggerItem key={product.id}>
                  <Link
                    href={`/products/${product.slug}`}
                    className="group block bg-white rounded-xl shadow-sm ring-1 ring-gray-900/5 overflow-hidden transition-all duration-300 hover:-translate-y-1 hover:ring-2 hover:ring-primary-400/60 hover:shadow-glow-md"
                  >
                    <div className="h-48 bg-gray-100 overflow-hidden flex items-center justify-center">
                      {product.images?.[0]?.url ? (
                        <img
                          src={product.images[0].url}
                          alt={product.name}
                          className="h-full w-full object-cover transition-transform duration-500 ease-out-expo group-hover:scale-110"
                        />
                      ) : (
                        <span className="text-4xl transition-transform duration-300 group-hover:scale-125 group-hover:-rotate-6">📦</span>
                      )}
                    </div>
                    <div className="p-4">
                      <div className="text-xs font-medium uppercase tracking-wide text-gray-400 mb-1">{product.brand?.name}</div>
                      <h3 className="font-semibold text-gray-900 mb-2 line-clamp-2 group-hover:text-primary-700 transition-colors">{product.name}</h3>
                      <div className="flex items-center gap-2">
                        <span className="text-lg font-bold text-primary-600">
                          ৳{product.price.toLocaleString()}
                        </span>
                        {product.compare_at_price && product.compare_at_price > product.price && (
                          <span className="text-sm text-gray-400 line-through">
                            ৳{product.compare_at_price.toLocaleString()}
                          </span>
                        )}
                      </div>
                      <div className="mt-2 text-sm text-gray-500">
                        {product.stock_quantity > 0 ? (
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
                    </div>
                  </Link>
                </StaggerItem>
              ))}
            </Stagger>
          )}
        </div>
      </div>
    </div>
  )
}
