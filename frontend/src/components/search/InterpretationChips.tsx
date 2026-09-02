'use client'

import { Info, Sparkles } from 'lucide-react'
import { Stagger, StaggerItem } from '@/components/motion'
import type { AISearchInterpretation } from '@/lib/api'

/**
 * "AI understood" block for the search page:
 * - chip row derived from the ai-search interpretation (budget, use case,
 *   category, brands, specs) — animated in with Stagger
 * - optional relaxation notes shown as a subtle hint line
 */

interface Chip {
  key: string
  label: string
  /** Accent tone for the chip. */
  tone: 'primary' | 'violet' | 'cyan'
}

const fmtBDT = (n: number) => `৳${Math.round(n).toLocaleString()}`

const titleCase = (s: string) =>
  (s || '')
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())

const capitalize = (s: string) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s)

function formatSpecValue(value: any): string {
  if (Array.isArray(value)) return value.map((v) => String(v)).join(', ')
  if (value === null || value === undefined) return ''
  return String(value)
}

export function buildChips(interp: AISearchInterpretation): Chip[] {
  const chips: Chip[] = []
  const min = typeof interp.budget_min === 'number' ? interp.budget_min : null
  const max = typeof interp.budget_max === 'number' ? interp.budget_max : null

  if (min !== null && max !== null) {
    chips.push({ key: 'budget', label: `Budget ৳${fmtBDT(min)} – ৳${fmtBDT(max)}`, tone: 'primary' })
  } else if (max !== null) {
    chips.push({ key: 'budget', label: `Budget ≤ ৳${fmtBDT(max)}`, tone: 'primary' })
  } else if (min !== null) {
    chips.push({ key: 'budget', label: `Budget ≥ ৳${fmtBDT(min)}`, tone: 'primary' })
  }

  if (interp.use_case) {
    chips.push({ key: 'use-case', label: capitalize(String(interp.use_case)), tone: 'violet' })
  }

  if (interp.category) {
    chips.push({ key: 'category', label: titleCase(String(interp.category)), tone: 'cyan' })
  } else if (Array.isArray(interp.category_candidates)) {
    interp.category_candidates.slice(0, 3).forEach((c, i) => {
      chips.push({ key: `category-${i}`, label: titleCase(String(c)), tone: 'cyan' })
    })
  }

  if (Array.isArray(interp.brands)) {
    interp.brands.slice(0, 4).forEach((b, i) => {
      chips.push({ key: `brand-${i}`, label: titleCase(String(b)), tone: 'violet' })
    })
  }

  if (interp.specs && typeof interp.specs === 'object') {
    Object.entries(interp.specs)
      .slice(0, 5)
      .forEach(([key, value]) => {
        const formatted = formatSpecValue(value)
        if (!formatted) return
        chips.push({ key: `spec-${key}`, label: `${titleCase(key)}: ${formatted}`, tone: 'primary' })
      })
  }

  return chips
}

const TONE_CLASSES: Record<Chip['tone'], string> = {
  primary: 'border-primary-200/80 bg-primary-50/80 text-primary-800',
  violet: 'border-violet-200/80 bg-violet-50/80 text-violet-800',
  cyan: 'border-cyan-200/80 bg-cyan-50/80 text-cyan-800',
}

export default function InterpretationChips({
  interpretation,
}: {
  interpretation: AISearchInterpretation
}) {
  const chips = buildChips(interpretation)
  const notes = Array.isArray(interpretation.notes) ? interpretation.notes.filter(Boolean) : []

  if (chips.length === 0 && notes.length === 0) return null

  return (
    <div className="mb-6">
      {chips.length > 0 && (
        <>
          <p className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-gray-400">
            <Sparkles className="h-3.5 w-3.5 text-primary-500" />
            AI understood your search as
          </p>
          <Stagger className="flex flex-wrap gap-2" gap={0.05}>
            {chips.map((chip) => (
              <StaggerItem key={chip.key} y={10}>
                <span
                  className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium backdrop-blur transition-colors ${TONE_CLASSES[chip.tone]}`}
                >
                  {chip.label}
                </span>
              </StaggerItem>
            ))}
          </Stagger>
        </>
      )}

      {notes.length > 0 && (
        <p className="mt-2.5 flex items-start gap-1.5 text-xs italic text-gray-500">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-gray-400" />
          <span>{notes.join(' · ')}</span>
        </p>
      )}
    </div>
  )
}
