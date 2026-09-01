---
plan name: techcommerce-upgrade
plan description: Seed data, panel, motion, smart search
plan status: done
---

## Idea
Four upgrades to TechCommerce (FastAPI + Next.js 14/Tailwind): (1) Mass-populate the database with hundreds-to-thousands of real-world tech products across all 15 categories via a data-driven generator (real model names like RTX 4070 Super, Ryzen 7 7800X3D, Galaxy S24, with realistic BDT prices, specs, stock, plus reviews and coupons); (2) Secure and enhance the admin panel — enforce real JWT+role verification on all /api/v1/admin endpoints (currently a no-op stub) and upgrade the dashboard with revenue charts, order stats, top products, low-stock alerts; (3) Rich design polish — add framer-motion, animated hero, staggered card reveals, scroll-triggered animations, gradient/glass accents, micro-interactions on storefront pages; (4) AI search — local natural-language parser endpoint (budget/use-case/category/brand/spec extraction from queries like 'gaming laptop under 100k for university') wired into /api/v1/catalog and the frontend search page. No external LLM or API keys required.

## Implementation
- [object Object]
- [object Object]
- [object Object]
- [object Object]
- [object Object]
- [object Object]
- [object Object]

## Required Specs
<!-- SPECS_START -->
- techcommerce-upgrades
<!-- SPECS_END -->