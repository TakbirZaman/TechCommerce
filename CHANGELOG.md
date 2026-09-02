# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Real-world catalog at scale: `scripts/seed_catalog.py` data-driven generator (15 categories, spec templates for all 15, ~1,100 real-model products with BDT prices/specs/stock, 2,944 reviews, 5 coupons, 52 valid sample orders, deterministic + idempotent) wired into `scripts/seed.py`.
- `scripts/scrape_bd.py`: polite scraper for Bangladeshi retailers — Startech (HTML), Ryans (HTML), MC Solution (WooCommerce Store API); per-host rate limiting, disk cache, 429/503 backoff, price sanity bounds; 3,109 real products imported (sumashtech skipped: Nuxt SPA + robots.txt; computermania skipped: Cloudflare 403).
- `scripts/backfill_numeric_specs.py`: unit-aware `numeric_value` backfill from spec text (1,633 rows).
- AI search: `core/services/ai_search.py` local natural-language parser (BDT budget shorthand, use-cases, category intent, brand aliases, spec keywords with unit-family text fallback) + `GET /api/v1/catalog/ai-search` (scored results + parsed interpretation + graceful filter relaxation).
- Admin analytics API `GET /api/v1/admin/analytics` (30-day zero-filled revenue series, orders by status, top products, low stock, recent orders) + audit logging on all 22 admin mutation sites.
- Frontend: rebuilt admin dashboard (recharts area/donut charts, animated stat tiles, low-stock + recent-orders tables); AI-first `/search` with interpretation chips, % match badges, stale-response guard, silent fallback to normal search.
- Motion system: framer-motion v13, reusable primitives (`components/motion/`), animated hero, staggered grid reveals, scroll-triggered sections, glass navbar, cart transitions; `prefers-reduced-motion` respected throughout.
- Tests: `tests/test_admin_security.py` (16), `tests/test_ai_search.py` (55), `tests/test_ai_search_db.py` (8) — suite now 153 passing.

### Changed
- Admin API: real JWT signature+expiry+role verification (`get_current_admin_user`) enforced router-level on every `/api/v1/admin` endpoint (was a no-op Bearer-prefix stub); 401/403 semantics.
- Product images for generated catalog: 15 category SVG placeholders; scraped products reference source image URLs.
- Brand data hygiene: scraper name-prefix brands remapped (iPhone→Apple, ROG→ASUS, Legion→Lenovo, …), case-duplicate brands merged, deterministic stock spread for scraped items.
- `render.yaml`: `JWT_SECRET_KEY` now generated at deploy; local dev logs a warning when the default secret is used.

### Fixed
- Dev environment: Next.js rewrites proxy failed intermittently (`path-to-regexp` treats the `:8000` port in the rewrite destination as a route param → 500s under browser-level parallelism). Browser now calls the API directly (`NEXT_PUBLIC_API_URL` in committed `frontend/.env.development`); images resolve via new `assetUrl()` helper across all pages.
- Admin panel: `/admin/login` was wrapped by the admin layout's auth guard → infinite `/admin/login` redirect loop (login form could never render). Guard now exempts the login page and renders it without admin chrome.
- Products listing: passes proper filter object to the API (`page`/`page_size` included — a string was being char-indexed by `Object.entries`) and gained working Previous/Next pagination (was: only first 24 products, no way forward).
- `scripts/scrape_bd.py` `unique_slug` infinite loop (fallback checked the wrong variable).
- `POST /api/v1/admin/users` no longer returns `password_hash`/`reset_token` (safe field whitelist).
- 2 orphaned `order_items` FK violations repaired; all 4,217 slugs/SKUs unique; `PRAGMA foreign_key_check` clean.
- AI-search spec-key coverage (`ram`, `ssd`, `gpu_graphics`, `refresh_rate_hz`, …) so scraped products are reachable by spec queries; garbage queries return 0 results (frontend falls back) instead of showing unrelated products.
- Search score badge normalization (per-result-set %), stale-response race, UTC day-shift in analytics chart labels, `router.push` instead of full-page reload.
