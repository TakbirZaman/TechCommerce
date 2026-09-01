# Active Context — TechCommerce

> Rolling memory. Updated at end of each session. Source of truth: git history + state docs.

## Current state (2026-09-02)
**Plan `techcommerce-upgrade` COMPLETE — pending user commit approval.**
All 4 requested features delivered + BD retailer scraping (mid-session addition). Full working tree is UNCOMMITTED on `main` (base: `6bea1ee`).

## What was delivered
1. **Catalog at scale** — `scripts/seed_catalog.py` (generator, 15 categories, spec templates ×15, reviews, coupons, 52 sample orders) + `scripts/scrape_bd.py` (Startech/Ryans/MC Solution; sumashtech=Nuxt SPA and computermania=Cloudflare skipped with reasons). DB: **4,217 products** (1,095 generated + 3,109 scraped + 13 legacy), 2,944 reviews, 5 coupons, 52 orders, 0 FK violations, unique slugs/SKUs. Numeric spec backfill: +1,633 rows (`scripts/backfill_numeric_specs.py`, idempotent).
2. **Admin secure + dashboard** — real JWT+role enforcement (router-level, all endpoints), audit logs on 22 mutation sites, `GET /api/v1/admin/analytics` (30d revenue, status donut, top products, low stock, recent orders), rebuilt `admin/page.tsx` with recharts. 16 security tests.
3. **Design/motion** — framer-motion v13, design tokens (glow/gradients/glass), motion primitives (`components/motion/`), animated hero/products/detail/cart/navbar, reduced-motion respected.
4. **AI search** — `core/services/ai_search.py` local NL parser (BDT budgets, use-cases, categories, brands, specs w/ unit-aware text fallback), `GET /api/v1/catalog/ai-search`, AI-first `/search` with interpretation chips + silent fallback. 63 parser+DB tests.

## Quality gates (all passed)
pytest **153 passed** · `next build` green (22 routes) · live smoke: auth 401/200, garbage query → 0, recall "rtx 4070" → 10, no `password_hash` leak, Z-suffixed timestamps · @reviewer + @requirements-reviewer runs: CRITICAL/HIGH findings all fixed (slug-loop, JWT-secret warn+render.yaml, users leak, spec-key recall, garbage-query fallback, stale-response guard, chart tz).

## Known deferred (LOW, from reviewer #16–18)
- Seed `NOW = datetime.now` makes fresh-from-scratch re-seed dates non-deterministic (idempotency unaffected)
- `_backfill_existing_products` O(N) queries (seed-time only)
- `toLocaleString` without explicit locale in fmtBDT (theoretical hydration mismatch)

## Next actions (for a fresh session)
- [ ] Commit pending changes (user approval requested; suggest logical commits: seed+scraper, admin security+analytics, ai-search, frontend polish, chore deps)
- [ ] Set `JWT_SECRET_KEY` in production env (render.yaml now generates it; local dev warns)
- [ ] Optional: retry computermania via residential proxy/Playwright if more catalog depth wanted; ryans `--deep` for richer specs
