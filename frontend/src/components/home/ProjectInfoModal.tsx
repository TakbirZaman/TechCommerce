'use client'

import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { ArrowUpRight, Github, Info, Languages, Wrench, X } from 'lucide-react'

const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1]

const REPO = 'https://github.com/TakbirZaman/TechCommerce'

const TOOL_GROUPS = [
  { group: 'Frontend', items: ['Next.js 15', 'React 19', 'TypeScript', 'Tailwind CSS'] },
  { group: 'Backend', items: ['FastAPI', 'SQLAlchemy', 'Celery', 'Redis'] },
  { group: 'Platform', items: ['Docker', 'Nginx', 'PostgreSQL'] },
]

const LANGUAGES = [
  { name: 'TypeScript', color: 'bg-blue-500' },
  { name: 'Python', color: 'bg-yellow-400' },
  { name: 'JavaScript', color: 'bg-amber-500' },
  { name: 'CSS', color: 'bg-sky-400' },
]

const GITHUB_LINKS = [
  { label: 'Repository', hint: 'Source code & docs', href: REPO },
  { label: 'Issues', hint: 'Report a bug or request a feature', href: `${REPO}/issues` },
  { label: 'Pull Requests', hint: 'Contribute to the project', href: `${REPO}/pulls` },
]

function SectionLabel({ icon: Icon, children }: { icon: typeof Wrench; children: string }) {
  return (
    <p className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
      <Icon className="h-3.5 w-3.5 text-primary-500" />
      {children}
    </p>
  )
}

export function ProjectInfoModal() {
  const [open, setOpen] = useState(false)
  const reduceMotion = useReducedMotion()
  const closeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) return

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    window.addEventListener('keydown', onKeyDown)
    closeRef.current?.focus()

    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-2 rounded-full border border-white/25 bg-white/10 px-4 py-1.5 text-sm font-medium text-primary-100 backdrop-blur-md transition-colors duration-300 hover:bg-white/20 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-white/70"
      >
        <Info className="h-4 w-4" />
        Project Details
      </button>

      <AnimatePresence>
        {open && (
          <div
            className="fixed inset-0 z-[60] flex items-end justify-center p-4 sm:items-center"
            role="dialog"
            aria-modal="true"
            aria-labelledby="project-info-title"
          >
            {/* Backdrop */}
            <motion.button
              type="button"
              aria-label="Close project details"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.25 }}
              onClick={() => setOpen(false)}
              className="absolute inset-0 cursor-default bg-slate-900/60 backdrop-blur-sm"
            />

            {/* Panel */}
            <motion.div
              initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 32, scale: 0.97 }}
              animate={reduceMotion ? { opacity: 1 } : { opacity: 1, y: 0, scale: 1 }}
              exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 24, scale: 0.97 }}
              transition={{ duration: 0.32, ease: EASE }}
              className="relative max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white shadow-2xl ring-1 ring-gray-900/10"
            >
              {/* Header */}
              <div className="relative border-b border-gray-100 bg-gradient-to-br from-primary-600 to-primary-800 px-6 py-5 text-white">
                <button
                  ref={closeRef}
                  type="button"
                  onClick={() => setOpen(false)}
                  aria-label="Close"
                  className="absolute right-4 top-4 rounded-full p-1.5 text-white/70 transition-colors hover:bg-white/15 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-white/70"
                >
                  <X className="h-4 w-4" />
                </button>
                <span className="inline-flex items-center gap-1.5 rounded-full border border-white/25 bg-white/10 px-2.5 py-1 text-[11px] font-medium uppercase tracking-wide">
                  <Github className="h-3 w-3" /> Open Source
                </span>
                <h2 id="project-info-title" className="mt-3 text-xl font-bold">
                  TechCommerce
                </h2>
                <p className="mt-1 text-sm text-primary-100">
                  A full-stack e-commerce platform with AI-powered recommendations, a PC builder,
                  and a product comparison engine.
                </p>
              </div>

              <div className="space-y-6 px-6 py-6">
                {/* Tools */}
                <section>
                  <SectionLabel icon={Wrench}>Tools &amp; Platforms</SectionLabel>
                  <div className="space-y-3">
                    {TOOL_GROUPS.map((group) => (
                      <div key={group.group}>
                        <p className="text-xs font-medium text-gray-400">{group.group}</p>
                        <div className="mt-1.5 flex flex-wrap gap-2">
                          {group.items.map((item) => (
                            <span
                              key={item}
                              className="rounded-md bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-700 ring-1 ring-gray-900/5"
                            >
                              {item}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </section>

                {/* Languages */}
                <section>
                  <SectionLabel icon={Languages}>Languages</SectionLabel>
                  <div className="flex flex-wrap gap-2">
                    {LANGUAGES.map((lang) => (
                      <span
                        key={lang.name}
                        className="inline-flex items-center gap-2 rounded-md bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-700 ring-1 ring-gray-900/5"
                      >
                        <span className={`h-2 w-2 rounded-full ${lang.color}`} aria-hidden />
                        {lang.name}
                      </span>
                    ))}
                  </div>
                </section>

                {/* GitHub links */}
                <section>
                  <SectionLabel icon={Github}>GitHub</SectionLabel>
                  <ul className="divide-y divide-gray-100 rounded-xl ring-1 ring-gray-900/5">
                    {GITHUB_LINKS.map((link) => (
                      <li key={link.label}>
                        <a
                          href={link.href}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="group flex items-center justify-between gap-3 px-4 py-3 transition-colors hover:bg-gray-50"
                        >
                          <span>
                            <span className="block text-sm font-medium text-gray-900 group-hover:text-primary-600">
                              {link.label}
                            </span>
                            <span className="block text-xs text-gray-500">{link.hint}</span>
                          </span>
                          <ArrowUpRight className="h-4 w-4 shrink-0 text-gray-400 transition-transform duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-primary-600" />
                        </a>
                      </li>
                    ))}
                  </ul>
                </section>
              </div>

              {/* Footer */}
              <div className="border-t border-gray-100 bg-gray-50 px-6 py-3 text-center text-xs text-gray-500">
                MIT License &middot; Built by Takbir Zaman &amp; Ibrar Amin
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  )
}
