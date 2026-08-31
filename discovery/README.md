# Product Discovery Module (`feature/discovery`)

Self-contained scaffold for the Discovery system described in the project
brief. It integrates with `feature/core-platform` (auth, users, categories,
brands) and `feature/commerce` (products, orders, cart) **by contract, not
by copy** — see `INTEGRATION.md` for exactly what to wire up.

No existing repository for `feature/core-platform` / `feature/commerce` was
available while building this, so `backend/app/models/stubs.py` defines
minimal versions of the models this module depends on (`Product`, `Brand`,
`Category`, `User`, `Order`, `OrderItem`) purely so the module is runnable
and testable on its own. **These stubs must be deleted and replaced with
real imports during integration** — do not deploy them.

## What's implemented

| Section | Feature | Where |
|---|---|---|
| 3-4 | Search + ranking abstraction | `backend/app/api/v1/search.py`, `services/ranking.py` |
| 5 | Autocomplete (debounced, cached) | `backend/app/api/v1/autocomplete.py`, `frontend/hooks/useDebounce.ts` |
| 6 | Dynamic filter engine (data-driven, not hard-coded per category) | `backend/app/services/filter_engine.py` |
| 7-8 | Composable sorting + URL-based filter state | `frontend/lib/searchParams.ts` |
| 9-11 | Comparison + compatibility rules + table UI | `backend/app/services/comparison.py`, `frontend/components/discovery/ComparisonTable.tsx` |
| 12 | Product detail DTOs | `backend/app/schemas/product.py` |
| 13-17 | Reviews, verified purchase, moderation, rating aggregation | `backend/app/models/review.py`, `services/verified_purchase.py`, `services/rating_aggregation.py` |
| 18-19 | Price history (append-only) + chart | `backend/app/models/price_history.py`, `frontend/components/discovery/PriceHistoryChart.tsx` |
| 20 | Related products abstraction | `backend/app/services/related_products.py` |
| 21-22 | Brand & category pages (cached) | `backend/app/api/v1/brands.py`, `categories.py` |
| 26-27 | List/Detail DTO split + Redis caching w/ invalidation | `backend/app/core/cache.py` |
| 28 | SEO metadata (`generateMetadata`, canonical, OG) | `frontend/app/**/page.tsx` |
| 31 | Admin discovery controls | `backend/app/api/v1/admin_discovery.py` |
| 32 | Tests | `backend/app/tests/` (16 passing against SQLite) |

## Explicitly NOT implemented (per Section 33)

No ML ranking, no ML related-products/recommendation engine, no AI advisor,
no LLM-generated specs, no fabricated benchmark/price data. Every place
where the intelligence branch plugs in is a named abstraction
(`RankingStrategy`, `RelatedProductsStrategy`) with one simple, explainable
default implementation.

## Running the backend standalone

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Requires Postgres + Redis locally (see `app/core/config.py` for env vars,
prefixed `DISCOVERY_`).

## Running tests

```bash
cd backend
pip install -r requirements.txt
pytest app/tests -q
```

16 tests pass against SQLite in-memory (comparison rules, reviews/verified
purchase/duplicate prevention, price history, related products, filter
engine). Tests that depend on Postgres-only SQL (`to_tsvector`/`ts_rank`,
JSON-path filtering in `search.py`) should be run against a real Postgres
instance in CI — that's noted in `backend/app/tests/conftest.py`.

## Frontend

`frontend/` contains the Next.js App Router pieces for this feature only
(pages, components, hooks, store, lib) meant to be merged into the main
app's `app/` directory — it is not a standalone deployable app. It assumes
shadcn/ui's Tailwind tokens (`bg-background`, `text-muted-foreground`, etc.)
already exist in the host app.

## Directory map

```
backend/app/
  core/        config, redis cache helpers, shared deps (STUB: auth)
  models/      review.py, price_history.py, featured.py (real) + stubs.py (STUB)
  schemas/     Pydantic DTOs, split List vs Detail
  services/    ranking.py, related_products.py, filter_engine.py,
               comparison.py, rating_aggregation.py, verified_purchase.py
  api/v1/      one router per feature area
  tests/       pytest suite
  alembic/     migration for the new discovery-owned tables

frontend/
  app/         search, products/[category], compare, brands/[slug], categories/[slug]
  components/discovery/  SearchBar, FilterPanel, ComparisonTable, ReviewForm, PriceHistoryChart
  hooks/       useDebounce, useProductSearch, useAutocomplete
  store/       comparisonStore (zustand)
  lib/         api.ts, searchParams.ts (URL filter state)
```
