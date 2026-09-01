'use client'

import { motion, useReducedMotion } from 'framer-motion'
import Link from 'next/link'
import { Search, Sparkles } from 'lucide-react'

const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1]

const HEADLINE_WORDS: { text: string; gradient: boolean }[] = [
  { text: 'Find', gradient: false },
  { text: 'Your', gradient: false },
  { text: 'Perfect', gradient: true },
  { text: 'Tech', gradient: true },
]

const POPULAR_LINKS = [
  { href: '/search?q=laptop', label: 'Laptops' },
  { href: '/search?q=phone', label: 'Phones' },
  { href: '/search?q=monitor', label: 'Monitors' },
  { href: '/pc-builder', label: 'Build a PC' },
]

export function Hero() {
  const reduceMotion = useReducedMotion()

  const container = {
    hidden: {},
    show: { transition: { staggerChildren: reduceMotion ? 0 : 0.09, delayChildren: 0.1 } },
  }

  const word = reduceMotion
    ? { hidden: { opacity: 0 }, show: { opacity: 1, transition: { duration: 0.4 } } }
    : {
        hidden: { y: '110%' },
        show: { y: '0%', transition: { duration: 0.7, ease: EASE } },
      }

  return (
    <section className="relative overflow-hidden bg-brand-gradient text-white">
      {/* Floating decorative gradient blobs */}
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="absolute -top-24 -left-24 h-96 w-96 rounded-full bg-primary-400/30 blur-3xl animate-float" />
        <div className="absolute top-1/3 -right-32 h-[28rem] w-[28rem] rounded-full bg-purple-500/25 blur-3xl animate-float-slow" />
        <div className="absolute -bottom-32 left-1/3 h-80 w-80 rounded-full bg-sky-400/20 blur-3xl animate-glow-pulse" />
        {/* Soft vignette to keep text legible */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_0%,rgba(15,23,42,0.35)_100%)]" />
      </div>

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 md:py-28">
        <div className="text-center">
          {/* Badge */}
          <motion.div
            initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 16 }}
            animate={reduceMotion ? { opacity: 1 } : { opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: EASE }}
            className="mb-6 inline-flex items-center gap-2 rounded-full border border-white/25 bg-white/10 px-4 py-1.5 text-sm font-medium text-primary-100 backdrop-blur-md"
          >
            <Sparkles className="h-4 w-4 text-sky-300" />
            AI-Powered Product Discovery
          </motion.div>

          {/* Headline — word-by-word masked rise */}
          <motion.h1
            variants={container}
            initial="hidden"
            animate="show"
            className="text-4xl md:text-6xl font-extrabold tracking-tight mb-6"
            aria-label="Find Your Perfect Tech"
          >
            {HEADLINE_WORDS.map((w) => (
              <span key={w.text} className="inline-block overflow-hidden pb-1 -mb-1 align-bottom">
                <motion.span
                  variants={word}
                  className={`inline-block ${w.gradient ? 'gradient-text' : ''}`}
                >
                  {w.text}&nbsp;
                </motion.span>
              </span>
            ))}
          </motion.h1>

          {/* Subheading */}
          <motion.p
            initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 20 }}
            animate={reduceMotion ? { opacity: 1 } : { opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.45, ease: EASE }}
            className="text-xl md:text-2xl text-primary-100 mb-10 max-w-3xl mx-auto"
          >
            AI-powered recommendations to help you find the right laptop, phone, or component.
            Compare products, build your PC, and get expert advice.
          </motion.p>

          {/* Search pill CTA */}
          <motion.div
            initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 20 }}
            animate={reduceMotion ? { opacity: 1 } : { opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.6, ease: EASE }}
            className="max-w-2xl mx-auto"
          >
            <Link href="/advisor" className="group block">
              <motion.div
                whileHover={reduceMotion ? undefined : { scale: 1.02 }}
                whileTap={reduceMotion ? undefined : { scale: 0.99 }}
                transition={{ duration: 0.2, ease: EASE }}
                className="relative flex items-center cursor-pointer rounded-2xl bg-white/95 shadow-2xl shadow-primary-900/40 ring-1 ring-white/60 transition-shadow duration-300 group-hover:shadow-glow-lg"
              >
                <Search className="absolute left-5 h-6 w-6 text-gray-400 transition-colors group-hover:text-primary-500" />
                <span className="w-full py-4 pl-14 pr-6 text-left text-gray-400 md:text-lg truncate">
                  Try: &ldquo;Suggest a laptop under 100k for programming&rdquo;
                </span>
                <span className="hidden sm:inline-flex mr-3 items-center gap-1 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 px-4 py-2 text-sm font-semibold text-white shadow-md shadow-primary-600/30">
                  Ask AI
                </span>
              </motion.div>
            </Link>
          </motion.div>

          {/* Popular links */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.8 }}
            className="mt-8 flex flex-wrap justify-center items-center gap-x-5 gap-y-2 text-sm"
          >
            <span className="text-primary-200">Popular:</span>
            {POPULAR_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="group relative text-white/90 transition-colors hover:text-white"
              >
                {link.label}
                <span className="absolute -bottom-0.5 left-0 h-px w-full origin-left scale-x-0 bg-gradient-to-r from-sky-300 to-purple-300 transition-transform duration-300 group-hover:scale-x-100" />
              </Link>
            ))}
          </motion.div>
        </div>
      </div>
    </section>
  )
}
