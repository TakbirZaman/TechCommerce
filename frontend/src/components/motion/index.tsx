'use client'

import { motion, useReducedMotion } from 'framer-motion'
import Link from 'next/link'
import type { ReactNode } from 'react'

/**
 * Shared motion primitives for the storefront.
 *
 * Rules baked into every component here:
 * - Never animates layout properties (only opacity + transform) → zero layout shift.
 * - Respects `prefers-reduced-motion`: reveals fall back to pure opacity fades,
 *   hover/tap effects are disabled entirely.
 */

const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1]

const VIEWPORT = { once: true, margin: '-64px' } as const

interface FadeInProps {
  children: ReactNode
  className?: string
  /** Seconds to wait before the reveal starts. */
  delay?: number
  /** Vertical offset in px the element rises from. */
  y?: number
}

/** Scroll-triggered reveal: fades up into view the first time it enters the viewport. */
export function FadeIn({ children, className, delay = 0, y = 24 }: FadeInProps) {
  const reduceMotion = useReducedMotion()

  return (
    <motion.div
      className={className}
      initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y }}
      whileInView={reduceMotion ? { opacity: 1 } : { opacity: 1, y: 0 }}
      viewport={VIEWPORT}
      transition={{ duration: 0.6, delay, ease: EASE }}
    >
      {children}
    </motion.div>
  )
}

interface StaggerProps {
  children: ReactNode
  className?: string
  /** Seconds between each child's entrance. */
  gap?: number
  /** Seconds to wait before the first child starts. */
  delay?: number
}

/**
 * Stagger container: orchestrates its `StaggerItem` children with a
 * cascading entrance when scrolled into view.
 */
export function Stagger({ children, className, gap = 0.08, delay = 0 }: StaggerProps) {
  const reduceMotion = useReducedMotion()

  return (
    <motion.div
      className={className}
      initial="hidden"
      whileInView="show"
      viewport={VIEWPORT}
      variants={{
        hidden: {},
        show: {
          transition: {
            staggerChildren: reduceMotion ? 0 : gap,
            delayChildren: delay,
          },
        },
      }}
    >
      {children}
    </motion.div>
  )
}

interface StaggerItemProps {
  children: ReactNode
  className?: string
  /** Vertical offset in px the item rises from. */
  y?: number
}

/** Child of `Stagger` — inherits the container's orchestration. */
export function StaggerItem({ children, className, y = 24 }: StaggerItemProps) {
  const reduceMotion = useReducedMotion()

  return (
    <motion.div
      className={className}
      variants={{
        hidden: reduceMotion ? { opacity: 0 } : { opacity: 0, y },
        show: {
          opacity: 1,
          y: 0,
          transition: { duration: 0.55, ease: EASE },
        },
      }}
    >
      {children}
    </motion.div>
  )
}

interface HoverLiftProps {
  children: ReactNode
  className?: string
  /** Pixels to float up on hover. */
  lift?: number
}

/**
 * Wrap a card to make it float up on hover (with a soft settle on press).
 * Transform-only → no layout shift.
 */
export function HoverLift({ children, className, lift = 6 }: HoverLiftProps) {
  const reduceMotion = useReducedMotion()

  if (reduceMotion) {
    return <div className={className}>{children}</div>
  }

  return (
    <motion.div
      className={className}
      whileHover={{ y: -lift, transition: { duration: 0.25, ease: EASE } }}
      whileTap={{ scale: 0.99, transition: { duration: 0.15 } }}
    >
      {children}
    </motion.div>
  )
}

/** A `next/link` that can be animated with motion props (whileHover, whileTap…). */
export const MotionLink = motion.create(Link)
