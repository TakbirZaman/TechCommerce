'use client'

import { useEffect, useRef, useState } from 'react'

interface AnimatedNumberProps {
  value: number
  /** Formatter for the interpolated value. Defaults to rounded + locale grouping. */
  format?: (n: number) => string
  /** Total duration of the count-up in ms. */
  duration?: number
  className?: string
}

/**
 * Count-up number: eases from 0 to `value` on mount / value change.
 * Honors `prefers-reduced-motion` by jumping straight to the final value.
 */
export default function AnimatedNumber({
  value,
  format,
  duration = 1200,
  className,
}: AnimatedNumberProps) {
  const [display, setDisplay] = useState(0)
  const rafRef = useRef<number | null>(null)
  const fmt = format ?? ((n: number) => Math.round(n).toLocaleString())

  useEffect(() => {
    const reduceMotion =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches

    if (reduceMotion) {
      setDisplay(value)
      return
    }

    const start = performance.now()
    const from = 0

    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - t, 4) // ease-out-quart
      setDisplay(from + (value - from) * eased)
      if (t < 1) rafRef.current = requestAnimationFrame(tick)
    }

    rafRef.current = requestAnimationFrame(tick)
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
  }, [value, duration])

  return <span className={className}>{fmt(display)}</span>
}
