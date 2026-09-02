# Active Context — TechCommerce

> Rolling memory. Updated at end of each session. Source of truth: git history + state docs.

## Current state (2026-09-02)
**Plan `techcommerce-upgrade` COMPLETE — delivered, reviewed, browser-verified, and on GitHub.**
All work lives on branch `feature/techcommerce-upgrade` (6 commits: `3d3f04e` → `e3acc96`), pushed to the fork
**`ibraramin/TechCommerce`** and opened as **PR #1 → `TakbirZaman/TechCommerce`** (https://github.com/TakbirZaman/TechCommerce/pull/1).
Local `main` restored to pristine origin state (`6bea1ee`); repo checked out on the feature branch.

## What was delivered
1. **Catalog at scale** — `scripts/seed_catalog.py` (generator, 15 categories, spec templates ×15, reviews, coupons, 52 sample orders) + `scripts/scrape_bd.py` (Startech 1,705 / Ryans 797 / MC Solution 607; sumashtech=Nuxt SPA and computermania=Cloudflare skipped with reasons). DB: **4,217 products** (1,095 generated + 3,109 scraped + 13 legacy), 2,944 reviews, 5 coupons, 52 orders, 0 FK violations, unique slugs/SKUs. Numeric spec backfill: +1,633 rows (`scripts/backfill_numeric_specs.py`, idempotent).
2. **Admin secure + dashboard** — real JWT+role enforcement (router-level, all endpoints), audit logs on 22 mutation sites, `GET /api/v1/admin/analytics`, rebuilt `admin/page.tsx` with recharts. 16 security tests.
3. **Design/motion** — framer-motion v13, design tokens (glow/gradients/glass), motion primitives, animated hero/products/detail/cart/navbar, reduced-motion respected.
4. **AI search** — `core/services/ai_search.py` local NL parser (BDT budgets, use-cases, categories, brands, specs w/ unit-aware text fallback), `GET /api/v1/catalog/ai-search`, AI-first `/search` with interpretation chips + silent fallback. 63 parser+DB tests.

## Launch-blocking bugs found via real-browser testing (all fixed in `e3acc96`)
- Admin login: layout guard wrapped `/admin/login` → infinite redirect loop (login form never rendered). Guard now exempts it; login page renders bare.
- Products: no pagination + params passed as string got char-indexed. Proper object params (`page`/`page_size`) + Prev/Next UI.
- Dev API proxy: Next rewrites destination port `:8000` parsed as `:param` → intermittent 500s. Browser now calls the API directly (`frontend/.env.development`, committed); images resolve via `assetUrl()` across all pages.
- Verified in headless Chromium: login → dashboard with charts, page 2 pagination, AI search (10 results + chips), advisor (6 recommendations). `next build` green.

## Quality gates (all passed)
pytest **153 passed** · `next build` green (22 routes) · live smoke: auth 401/200, garbage query → 0, recall "rtx 4070" → 10, no `password_hash` leak, Z-suffixed timestamps · @reviewer + @requirements-reviewer verdicts addressed (CRITICAL/HIGH fixed: slug-loop, JWT-secret warn+render.yaml, users leak, spec-key recall, garbage-query fallback, stale-response guard, chart tz).

## Known deferred (LOW, from reviewer #16–18)
- Seed `NOW = datetime.now` makes fresh-from-scratch re-seed dates non-deterministic (idempotency unaffected)
- `_backfill_existing_products` O(N) queries (seed-time only)
- `toLocaleString` without explicit locale in fmtBDT (theoretical hydration mismatch)

## Next actions (for a fresh session)
- [ ] **TakbirZaman: review + merge PR #1** (or add `ibraramin` as collaborator to push branches directly)
- [ ] Set `JWT_SECRET_KEY` in production env (render.yaml now generates it; local dev warns)
- [ ] Optional: retry computermania via residential proxy/Playwright for more catalog depth; ryans `--deep` for richer specs
- [ ] After merge + fresh clone: `python scripts/seed.py && python scripts/scrape_bd.py` rebuilds the DB
