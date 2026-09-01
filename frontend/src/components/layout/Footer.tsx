import Link from 'next/link'

export function Footer() {
  return (
    <footer className="bg-gray-900 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div>
            <Link href="/" className="flex items-center mb-4">
              <span className="text-2xl font-bold text-primary-400">Tech</span>
              <span className="text-2xl font-bold text-white">Commerce</span>
            </Link>
            <p className="text-gray-400 text-sm">
              Your one-stop shop for all tech needs. AI-powered recommendations to help you find the perfect product.
            </p>
          </div>

          {/* Quick Links */}
          <div>
            <h3 className="text-lg font-semibold mb-4">Quick Links</h3>
            <ul className="space-y-2">
              <li>
                <Link href="/products" className="text-gray-400 hover:text-white text-sm">
                  All Products
                </Link>
              </li>
              <li>
                <Link href="/pc-builder" className="text-gray-400 hover:text-white text-sm">
                  PC Builder
                </Link>
              </li>
              <li>
                <Link href="/compare" className="text-gray-400 hover:text-white text-sm">
                  Compare Products
                </Link>
              </li>
              <li>
                <Link href="/advisor" className="text-gray-400 hover:text-white text-sm">
                  AI Advisor
                </Link>
              </li>
            </ul>
          </div>

          {/* Categories */}
          <div>
            <h3 className="text-lg font-semibold mb-4">Categories</h3>
            <ul className="space-y-2">
              <li>
                <Link href="/products?category=laptops" className="text-gray-400 hover:text-white text-sm">
                  Laptops
                </Link>
              </li>
              <li>
                <Link href="/products?category=phones" className="text-gray-400 hover:text-white text-sm">
                  Smartphones
                </Link>
              </li>
              <li>
                <Link href="/products?category=monitors" className="text-gray-400 hover:text-white text-sm">
                  Monitors
                </Link>
              </li>
              <li>
                <Link href="/products?category=components" className="text-gray-400 hover:text-white text-sm">
                  Components
                </Link>
              </li>
            </ul>
          </div>

          {/* Support */}
          <div>
            <h3 className="text-lg font-semibold mb-4">Support</h3>
            <ul className="space-y-2">
              <li>
                <Link href="/track-order" className="text-gray-400 hover:text-white text-sm">
                  Track Order
                </Link>
              </li>
              <li>
                <a href="#" className="text-gray-400 hover:text-white text-sm">
                  Contact Us
                </a>
              </li>
              <li>
                <a href="#" className="text-gray-400 hover:text-white text-sm">
                  FAQ
                </a>
              </li>
              <li>
                <a href="#" className="text-gray-400 hover:text-white text-sm">
                  Shipping Policy
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="border-t border-gray-800 mt-8 pt-8 text-center text-gray-400 text-sm">
          <p>&copy; {new Date().getFullYear()} TechCommerce. All rights reserved.</p>
        </div>
      </div>
    </footer>
  )
}
