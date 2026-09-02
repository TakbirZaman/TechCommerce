import Link from 'next/link'
import { Cpu, BarChart3, Shield, Truck, ArrowRight } from 'lucide-react'
import { FadeIn, Stagger, StaggerItem, HoverLift, MotionLink } from '@/components/motion'
import { Hero } from '@/components/home/Hero'

const FEATURES = [
  {
    icon: Cpu,
    title: 'AI Advisor',
    description: 'Tell us what you need, and our AI will find the perfect product for you.',
  },
  {
    icon: BarChart3,
    title: 'Compare Products',
    description: 'Side-by-side comparison of specs, prices, and features.',
  },
  {
    icon: Shield,
    title: 'PC Builder',
    description: 'Build your custom PC with real-time compatibility checking.',
  },
  {
    icon: Truck,
    title: 'Fast Delivery',
    description: 'Quick and reliable delivery across Bangladesh.',
  },
]

const CATEGORIES = [
  { slug: 'laptops', emoji: '💻', name: 'Laptops', tagline: 'From budget to gaming' },
  { slug: 'phones', emoji: '📱', name: 'Smartphones', tagline: 'Latest flagship & budget' },
  { slug: 'monitors', emoji: '🖥️', name: 'Monitors', tagline: '4K, Gaming, Ultrawide' },
  { slug: 'processors', emoji: '⚡', name: 'Processors', tagline: 'Intel & AMD CPUs' },
  { slug: 'graphics-cards', emoji: '🎮', name: 'Graphics Cards', tagline: 'NVIDIA & AMD GPUs' },
  { slug: 'ram', emoji: '🔧', name: 'RAM', tagline: 'DDR4 & DDR5 Memory' },
  { slug: 'storage', emoji: '💾', name: 'Storage', tagline: 'SSD & NVMe Drives' },
  { slug: 'motherboards', emoji: '🏗️', name: 'Motherboards', tagline: 'ATX, Micro-ATX, Mini' },
  { slug: 'tablets', emoji: '📋', name: 'Tablets', tagline: 'iPad & Android Tablets' },
  { slug: 'headsets', emoji: '🎧', name: 'Headsets', tagline: 'Gaming & Audio' },
]

export default function HomePage() {
  return (
    <div>
      {/* Hero Section */}
      <Hero />

      {/* Features / Trust Strip */}
      <section className="py-16 md:py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <FadeIn className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900">Why TechCommerce?</h2>
            <p className="mt-2 text-gray-600">Smart tools to help you make the right choice</p>
          </FadeIn>

          <Stagger className="grid grid-cols-1 md:grid-cols-4 gap-8" gap={0.12}>
            {FEATURES.map((feature) => (
              <StaggerItem key={feature.title}>
                <HoverLift className="h-full" lift={4}>
                  <div className="group h-full rounded-2xl bg-white p-6 text-center shadow-sm ring-1 ring-gray-900/5 transition-all duration-300 hover:shadow-glow-md hover:ring-primary-300/60">
                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-100 to-primary-50 ring-1 ring-primary-200/70 flex items-center justify-center mx-auto mb-4 transition-transform duration-300 group-hover:scale-110 group-hover:-rotate-3">
                      <feature.icon className="w-8 h-8 text-primary-600" />
                    </div>
                    <h3 className="text-lg font-semibold mb-2 text-gray-900">{feature.title}</h3>
                    <p className="text-gray-600 text-sm">{feature.description}</p>
                  </div>
                </HoverLift>
              </StaggerItem>
            ))}
          </Stagger>
        </div>
      </section>

      {/* Categories Section */}
      <section className="py-16 md:py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <FadeIn className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900">Shop by Category</h2>
            <p className="mt-2 text-gray-600">Find exactly what you&apos;re looking for</p>
          </FadeIn>

          <Stagger className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4" gap={0.06}>
            {CATEGORIES.map((category) => (
              <StaggerItem key={category.slug}>
                <HoverLift lift={6}>
                  <Link
                    href={`/products?category=${category.slug}`}
                    className="group flex h-full flex-col items-center rounded-xl bg-white p-6 text-center shadow-sm ring-1 ring-gray-900/5 transition-all duration-300 hover:ring-2 hover:ring-primary-400/60 hover:shadow-glow-md"
                  >
                    <span className="text-4xl mb-4 inline-block transition-transform duration-300 ease-out-expo group-hover:scale-125 group-hover:-rotate-6">
                      {category.emoji}
                    </span>
                    <h3 className="font-semibold text-gray-900 group-hover:text-primary-600 transition-colors">
                      {category.name}
                    </h3>
                    <p className="text-sm text-gray-500 mt-1">{category.tagline}</p>
                    <span className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-primary-600 opacity-0 -translate-x-1 transition-all duration-300 group-hover:opacity-100 group-hover:translate-x-0">
                      Explore <ArrowRight className="h-3 w-3" />
                    </span>
                  </Link>
                </HoverLift>
              </StaggerItem>
            ))}
          </Stagger>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative overflow-hidden py-16 md:py-20">
        {/* Animated gradient backdrop */}
        <div className="absolute inset-0 bg-gradient-to-r from-primary-600 via-primary-700 to-primary-900 bg-[length:200%_200%] animate-gradient-shift" />
        <div
          aria-hidden
          className="absolute -top-20 right-10 h-64 w-64 rounded-full bg-purple-500/20 blur-3xl animate-float-slow"
        />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <FadeIn>
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">Build Your Dream PC</h2>
            <p className="text-primary-100 mb-8 max-w-2xl mx-auto">
              Use our PC Builder tool to configure your perfect setup. Get real-time compatibility
              checks and price calculations.
            </p>
            <div className="flex flex-wrap justify-center gap-4">
              <MotionLink
                href="/pc-builder"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.97 }}
                className="inline-block bg-white text-primary-700 font-semibold px-8 py-3 rounded-lg shadow-lg shadow-primary-900/30 transition-shadow duration-300 hover:shadow-glow-lg"
              >
                Start Building →
              </MotionLink>
              <MotionLink
                href="/products"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.97 }}
                className="inline-block border-2 border-white/80 text-white font-semibold px-8 py-3 rounded-lg transition-colors duration-300 hover:bg-white hover:text-primary-700"
              >
                Browse All Products
              </MotionLink>
            </div>
          </FadeIn>
        </div>
      </section>
    </div>
  )
}
