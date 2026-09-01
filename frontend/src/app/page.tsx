import Link from 'next/link'
import { Search, Cpu, BarChart3, Shield, Truck, Star, Zap, Monitor } from 'lucide-react'

export default function HomePage() {
  return (
    <div>
      {/* Hero Section */}
      <section className="bg-gradient-to-r from-primary-600 to-primary-800 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div className="text-center">
            <h1 className="text-4xl md:text-5xl font-bold mb-6">
              Find Your Perfect Tech
            </h1>
            <p className="text-xl md:text-2xl text-primary-100 mb-8 max-w-3xl mx-auto">
              AI-powered recommendations to help you find the right laptop, phone, or component. 
              Compare products, build your PC, and get expert advice.
            </p>
            
            {/* Search Bar */}
            <div className="max-w-2xl mx-auto">
              <Link href="/advisor">
                <div className="relative cursor-pointer">
                  <input
                    type="text"
                    placeholder="Try: 'Suggest a laptop under 100k for programming'"
                    className="w-full pl-12 pr-6 py-4 text-gray-900 rounded-lg text-lg"
                    readOnly
                  />
                  <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 w-6 h-6" />
                </div>
              </Link>
            </div>

            <div className="mt-6 flex flex-wrap justify-center gap-4 text-sm">
              <span className="text-primary-200">Popular:</span>
              <Link href="/search?q=laptop" className="text-white hover:underline">Laptops</Link>
              <Link href="/search?q=phone" className="text-white hover:underline">Phones</Link>
              <Link href="/search?q=monitor" className="text-white hover:underline">Monitors</Link>
              <Link href="/pc-builder" className="text-white hover:underline">Build a PC</Link>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900">Why TechCommerce?</h2>
            <p className="mt-2 text-gray-600">Smart tools to help you make the right choice</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Cpu className="w-8 h-8 text-primary-600" />
              </div>
              <h3 className="text-lg font-semibold mb-2">AI Advisor</h3>
              <p className="text-gray-600 text-sm">
                Tell us what you need, and our AI will find the perfect product for you.
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <BarChart3 className="w-8 h-8 text-primary-600" />
              </div>
              <h3 className="text-lg font-semibold mb-2">Compare Products</h3>
              <p className="text-gray-600 text-sm">
                Side-by-side comparison of specs, prices, and features.
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Shield className="w-8 h-8 text-primary-600" />
              </div>
              <h3 className="text-lg font-semibold mb-2">PC Builder</h3>
              <p className="text-gray-600 text-sm">
                Build your custom PC with real-time compatibility checking.
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Truck className="w-8 h-8 text-primary-600" />
              </div>
              <h3 className="text-lg font-semibold mb-2">Fast Delivery</h3>
              <p className="text-gray-600 text-sm">
                Quick and reliable delivery across Bangladesh.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Categories Section */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900">Shop by Category</h2>
            <p className="mt-2 text-gray-600">Find exactly what you're looking for</p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
            <Link href="/products?category=laptops" className="group">
              <div className="bg-white rounded-lg shadow-md p-6 text-center hover:shadow-lg transition-shadow">
                <div className="text-4xl mb-4">💻</div>
                <h3 className="font-semibold text-gray-900 group-hover:text-primary-600">Laptops</h3>
                <p className="text-sm text-gray-500 mt-1">From budget to gaming</p>
              </div>
            </Link>

            <Link href="/products?category=phones" className="group">
              <div className="bg-white rounded-lg shadow-md p-6 text-center hover:shadow-lg transition-shadow">
                <div className="text-4xl mb-4">📱</div>
                <h3 className="font-semibold text-gray-900 group-hover:text-primary-600">Smartphones</h3>
                <p className="text-sm text-gray-500 mt-1">Latest flagship & budget</p>
              </div>
            </Link>

            <Link href="/products?category=monitors" className="group">
              <div className="bg-white rounded-lg shadow-md p-6 text-center hover:shadow-lg transition-shadow">
                <div className="text-4xl mb-4">🖥️</div>
                <h3 className="font-semibold text-gray-900 group-hover:text-primary-600">Monitors</h3>
                <p className="text-sm text-gray-500 mt-1">4K, Gaming, Ultrawide</p>
              </div>
            </Link>

            <Link href="/products?category=processors" className="group">
              <div className="bg-white rounded-lg shadow-md p-6 text-center hover:shadow-lg transition-shadow">
                <div className="text-4xl mb-4">⚡</div>
                <h3 className="font-semibold text-gray-900 group-hover:text-primary-600">Processors</h3>
                <p className="text-sm text-gray-500 mt-1">Intel & AMD CPUs</p>
              </div>
            </Link>

            <Link href="/products?category=graphics-cards" className="group">
              <div className="bg-white rounded-lg shadow-md p-6 text-center hover:shadow-lg transition-shadow">
                <div className="text-4xl mb-4">🎮</div>
                <h3 className="font-semibold text-gray-900 group-hover:text-primary-600">Graphics Cards</h3>
                <p className="text-sm text-gray-500 mt-1">NVIDIA & AMD GPUs</p>
              </div>
            </Link>

            <Link href="/products?category=ram" className="group">
              <div className="bg-white rounded-lg shadow-md p-6 text-center hover:shadow-lg transition-shadow">
                <div className="text-4xl mb-4">🔧</div>
                <h3 className="font-semibold text-gray-900 group-hover:text-primary-600">RAM</h3>
                <p className="text-sm text-gray-500 mt-1">DDR4 & DDR5 Memory</p>
              </div>
            </Link>

            <Link href="/products?category=storage" className="group">
              <div className="bg-white rounded-lg shadow-md p-6 text-center hover:shadow-lg transition-shadow">
                <div className="text-4xl mb-4">💾</div>
                <h3 className="font-semibold text-gray-900 group-hover:text-primary-600">Storage</h3>
                <p className="text-sm text-gray-500 mt-1">SSD & NVMe Drives</p>
              </div>
            </Link>

            <Link href="/products?category=motherboards" className="group">
              <div className="bg-white rounded-lg shadow-md p-6 text-center hover:shadow-lg transition-shadow">
                <div className="text-4xl mb-4">🏗️</div>
                <h3 className="font-semibold text-gray-900 group-hover:text-primary-600">Motherboards</h3>
                <p className="text-sm text-gray-500 mt-1">ATX, Micro-ATX, Mini</p>
              </div>
            </Link>

            <Link href="/products?category=tablets" className="group">
              <div className="bg-white rounded-lg shadow-md p-6 text-center hover:shadow-lg transition-shadow">
                <div className="text-4xl mb-4">📋</div>
                <h3 className="font-semibold text-gray-900 group-hover:text-primary-600">Tablets</h3>
                <p className="text-sm text-gray-500 mt-1">iPad & Android Tablets</p>
              </div>
            </Link>

            <Link href="/products?category=headsets" className="group">
              <div className="bg-white rounded-lg shadow-md p-6 text-center hover:shadow-lg transition-shadow">
                <div className="text-4xl mb-4">🎧</div>
                <h3 className="font-semibold text-gray-900 group-hover:text-primary-600">Headsets</h3>
                <p className="text-sm text-gray-500 mt-1">Gaming & Audio</p>
              </div>
            </Link>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 bg-primary-600">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">Build Your Dream PC</h2>
          <p className="text-primary-100 mb-8 max-w-2xl mx-auto">
            Use our PC Builder tool to configure your perfect setup. 
            Get real-time compatibility checks and price calculations.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Link
              href="/pc-builder"
              className="inline-block bg-white text-primary-600 font-semibold px-8 py-3 rounded-lg hover:bg-gray-100 transition-colors"
            >
              Start Building →
            </Link>
            <Link
              href="/products"
              className="inline-block border-2 border-white text-white font-semibold px-8 py-3 rounded-lg hover:bg-white hover:text-primary-600 transition-colors"
            >
              Browse All Products
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}
