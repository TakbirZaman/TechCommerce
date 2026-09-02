# Spec: techcommerce-upgrades

Scope: feature

# TechCommerce Upgrade — Feature Spec

Scope: feature (4 upgrades to the live FastAPI + Next.js 14 app under `main.py` / `frontend/`). Scaffolds `commerce-system/`, `discovery/`, `src/`, `api/` are OUT of scope.

## 1. Real-world catalog at scale
- New `scripts/seed_catalog.py` generates **1,000+ real-world tech products** across all 15 existing categories (Laptops, Smartphones, Monitors, Processors, Graphics Cards, RAM, Storage, Motherboards, Power Supplies, Cases, Keyboards, Mice, Headsets, Tablets, Accessories) by combining real model lines with real variants (e.g., "NVIDIA GeForce RTX 4070 Super" × ASUS TUF/MSI Gaming X/Gigabyte Windforce; "AMD Ryzen 7 7800X3D"; "Samsung Galaxy S24 Ultra").
- Every product: realistic **BDT market price** + compare_at_price, stock, SKU (deterministic), description, brand/category FK, and full `ProductSpecification` rows per category spec matrix.
- Spec templates + options created for **all 15 categories** (only 5 exist today) so compare/PC-builder/AI-search work catalog-wide.
- Generate plausible reviews (50–60% of products, 3–8 each, Bangladeshi reviewer names, verified mix) and 5+ active coupons.
- Seeding is **idempotent** (slug/SKU existence preloaded) and batch-fast (bulk inserts); does not slow app startup; existing 13 products and admin user preserved; deterministic (fixed RNG seed).

## 2. Admin: secure + analytics dashboard
- Replace the no-op `require_admin` in `core/routers/admin.py` with real validation: decode Bearer token via existing `core/services/token_service.py` (signature + expiry), load user, require `role in {admin, super_admin}` and `is_active`. Applied to **every** `/api/v1/admin` endpoint via FastAPI dependency; return 401 (bad/missing token) / 403 (non-admin).
- Audit-log admin mutations (action, resource, user, details) using existing `AuditLog` model.
- New `GET /api/v1/admin/analytics`: revenue by day (30d), orders by status, top products (units+revenue), low-stock list (≤10), recent orders (10), user count growth, total catalog/inventory stats.
- Frontend: rebuild `frontend/src/app/admin/page.tsx` with stat cards + charts (recharts) matching the new design language; keep existing admin pages working with enforced auth (frontend already sends Bearer tokens).

## 3. Storefront design: rich motion + polish
- Add `framer-motion`; extend `tailwind.config.js` + `globals.css` with keyframes, gradient/glass tokens, enhanced shadows.
- Animated hero with staggered entrance + CTA motion; scroll-triggered section reveals; staggered product-grid card entrances; hover micro-interactions (lift, image zoom, glow) on cards/buttons; animated nav; skeleton polish.
- Applies to home, product listing, product detail, cart, plus shared Navbar/Footer. Must remain professional, `next build` clean, no layout-shift jank; anim respects `prefers-reduced-motion`.

## 4. AI search (local NL parser, no external APIs)
- New `core/services/ai_search.py`: parse natural-language queries — budget ("under 100k", "50-80 thousand"), use-case (gaming/office/student/creator/server), category intent, brands, and spec keywords (RAM size, storage type/size, GPU model, CPU family, refresh rate, etc.).
- New `GET /api/v1/catalog/ai-search?q=...` returning `{interpretation: {budget, use_case, category, brands, specs}, results: [scored products], result_count}`. Scoring: filter-then-rank (hard filters where confident, soft boosts otherwise) using product specs + price.
- Frontend: NL search bar (navbar + `/search` page) hitting ai-search; show parsed interpretation chips ("Budget ≤ ৳100,000", "Use case: Gaming") above results; graceful fallback to normal search on parse failure.

## Conventions & validation
- Follow existing patterns: routers in `core/routers/` with `/api/v1/…` prefix registered in `main.py:include_router`; SQLAlchemy 2.0 mapped style; Pydantic v2 responses; BDT currency.
- No DB schema changes required (existing models suffice); no new Python deps beyond stdlib; frontend deps: framer-motion, recharts.
- Validation gates: `pytest` green, `next build` green, seeded counts verified, curl smoke tests on new endpoints, then @reviewer + @requirements-reviewer verdicts.