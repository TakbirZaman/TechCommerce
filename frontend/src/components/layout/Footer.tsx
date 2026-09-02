import Link from 'next/link'

export function Footer() {
  return (
    <footer className="relative bg-gray-900 text-white overflow-hidden">
      {/* Gradient accent line */}
      <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-primary-500/70 to-transparent" />
      {/* Ambient glow */}
      <div
        aria-hidden
        className="pointer-events-none absolute -bottom-32 left-1/2 -translate-x-1/2 h-64 w-[36rem] rounded-full bg-primary-600/10 blur-3xl"
      />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div>
            <Link href="/" className="inline-flex items-center mb-4">
              <span className="text-2xl font-extrabold gradient-text">Tech</span>
              <span className="text-2xl font-bold text-white">Commerce</span>
            </Link>
            <p className="text-gray-400 text-sm leading-relaxed">
              Your one-stop shop for all tech needs. AI-powered recommendations to help you find the perfect product.
            </p>
          </div>

          {/* Quick Links */}
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-200 mb-4">Quick Links</h3>
            <ul className="space-y-2">
              <li>
                <Link href="/products" className="group inline-flex items-center text-gray-400 hover:text-white text-sm transition-colors">
                  <span className="h-px w-0 bg-primary-400 transition-all duration-300 group-hover:w-3 group-hover:mr-2" />
                  All Products
                </Link>
              </li>
              <li>
                <Link href="/pc-builder" className="group inline-flex items-center text-gray-400 hover:text-white text-sm transition-colors">
                  <span className="h-px w-0 bg-primary-400 transition-all duration-300 group-hover:w-3 group-hover:mr-2" />
                  PC Builder
                </Link>
              </li>
              <li>
                <Link href="/compare" className="group inline-flex items-center text-gray-400 hover:text-white text-sm transition-colors">
                  <span className="h-px w-0 bg-primary-400 transition-all duration-300 group-hover:w-3 group-hover:mr-2" />
                  Compare Products
                </Link>
              </li>
              <li>
                <Link href="/advisor" className="group inline-flex items-center text-gray-400 hover:text-white text-sm transition-colors">
                  <span className="h-px w-0 bg-primary-400 transition-all duration-300 group-hover:w-3 group-hover:mr-2" />
                  AI Advisor
                </Link>
              </li>
            </ul>
          </div>

          {/* Categories */}
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-200 mb-4">Categories</h3>
            <ul className="space-y-2">
              <li>
                <Link href="/products?category=laptops" className="group inline-flex items-center text-gray-400 hover:text-white text-sm transition-colors">
                  <span className="h-px w-0 bg-primary-400 transition-all duration-300 group-hover:w-3 group-hover:mr-2" />
                  Laptops
                </Link>
              </li>
              <li>
                <Link href="/products?category=phones" className="group inline-flex items-center text-gray-400 hover:text-white text-sm transition-colors">
                  <span className="h-px w-0 bg-primary-400 transition-all duration-300 group-hover:w-3 group-hover:mr-2" />
                  Smartphones
                </Link>
              </li>
              <li>
                <Link href="/products?category=monitors" className="group inline-flex items-center text-gray-400 hover:text-white text-sm transition-colors">
                  <span className="h-px w-0 bg-primary-400 transition-all duration-300 group-hover:w-3 group-hover:mr-2" />
                  Monitors
                </Link>
              </li>
              <li>
                <Link href="/products?category=components" className="group inline-flex items-center text-gray-400 hover:text-white text-sm transition-colors">
                  <span className="h-px w-0 bg-primary-400 transition-all duration-300 group-hover:w-3 group-hover:mr-2" />
                  Components
                </Link>
              </li>
            </ul>
          </div>

          {/* Support */}
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-200 mb-4">Support</h3>
            <ul className="space-y-2">
              <li>
                <Link href="/track-order" className="group inline-flex items-center text-gray-400 hover:text-white text-sm transition-colors">
                  <span className="h-px w-0 bg-primary-400 transition-all duration-300 group-hover:w-3 group-hover:mr-2" />
                  Track Order
                </Link>
              </li>
              <li>
                <a href="#" className="group inline-flex items-center text-gray-400 hover:text-white text-sm transition-colors">
                  <span className="h-px w-0 bg-primary-400 transition-all duration-300 group-hover:w-3 group-hover:mr-2" />
                  Contact Us
                </a>
              </li>
              <li>
                <a href="#" className="group inline-flex items-center text-gray-400 hover:text-white text-sm transition-colors">
                  <span className="h-px w-0 bg-primary-400 transition-all duration-300 group-hover:w-3 group-hover:mr-2" />
                  FAQ
                </a>
              </li>
              <li>
                <a href="#" className="group inline-flex items-center text-gray-400 hover:text-white text-sm transition-colors">
                  <span className="h-px w-0 bg-primary-400 transition-all duration-300 group-hover:w-3 group-hover:mr-2" />
                  Shipping Policy
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="border-t border-gray-800 mt-8 pt-8 text-center text-gray-500 text-sm">
          <p>&copy; {new Date().getFullYear()} TechCommerce. All rights reserved.</p>
        </div>
      </div>
    </footer>
  )
}
