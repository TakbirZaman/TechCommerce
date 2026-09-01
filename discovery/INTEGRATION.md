# Integration Guide

This module was built without access to the real `feature/core-platform`
and `feature/commerce` codebases. It was designed around explicit,
narrow contracts so integration is a matter of swapping stub imports for
real ones — not rewriting logic. Follow these steps in order.

## 1. Replace stub models (`backend/app/models/stubs.py`)

Delete this file. Everywhere the discovery module does:

```python
from app.models.stubs import Product, Brand, Category, User, Order, OrderItem
```

replace with the real imports from core-platform/commerce, e.g.:

```python
from app.models.product import Product
from app.models.brand import Brand
from app.models.category import Category
from app.models.user import User
from app.commerce.models.order import Order, OrderItem
```

Required fields the discovery module assumes exist on each (map to your
real column names if they differ, or extend the real models):

- **Product**: `id, name, slug, sku, description, brand_id, category_id, price, status, stock_quantity, is_featured, is_visible, popularity_score, specifications (JSON), created_at, updated_at`
- **Category**: `id, name, slug, parent_id, description, filterable_spec_schema (JSON)` — the last one is new; see step 4.
- **Brand**: `id, name, slug, logo_url, description`
- **User**: `id, is_admin` (or however core-platform exposes admin role)
- **Order / OrderItem**: enough to answer "did user X buy product Y with a qualifying order status" — see `services/verified_purchase.py`.

If `specifications` doesn't exist as a JSON column on the real `Product`,
add it via migration — the filter engine, comparison table, and related-
products scoring all depend on it being structured data (Section 12: "do
not invent specifications").

## 2. Replace auth stubs (`backend/app/core/deps.py`)

Replace `get_current_user_optional`, `get_current_user_required`, and
`get_current_admin_user` with core-platform's real auth dependencies.
Keep the same call signatures used throughout `api/v1/*.py` (a dependency
that raises 401/403 appropriately and exposes `.id` / `.is_admin`) so no
router code needs to change.

## 3. Mount routers on the existing FastAPI app

Don't run `backend/app/main.py` in production — instead, in core-platform's
existing `app = FastAPI()`, add:

```python
from app.api.v1 import search, autocomplete, filters, comparison, reviews, price_history, related, brands, categories, admin_discovery
for r in [search, autocomplete, filters, comparison, reviews, price_history, related, brands, categories, admin_discovery]:
    app.include_router(r.router, prefix="/api/v1")
```

## 4. Migrations

Run `backend/alembic/versions/0001_discovery_tables.py` against the real
schema. Before running:
- Set `down_revision` to the current head of the core-platform/commerce
  migration chain.
- Confirm `products`, `users`, `orders` table names match (adjust FK
  targets in the migration if not).
- Uncomment the `filterable_spec_schema` column addition on `categories`
  if that table doesn't already support arbitrary category metadata.

## 5. Wire price-history recording into the REAL admin product-update endpoint

Don't use `backend/app/api/v1/price_history.py`'s `admin_update_price`
endpoint as-is in production — it's illustrative. Instead, import
`record_price_change(db, product, new_price, admin_id)` from
`app.api.v1.price_history` and call it inside commerce's existing
"update product" admin endpoint, in the same transaction, whenever price
changes. This keeps one source of truth for product writes (per the
brief: "do not rewrite existing... product... architecture").

## 6. Wire verified-purchase lookup to the real order schema

`services/verified_purchase.py`'s `QUALIFYING_ORDER_STATUSES` and the
join in `find_qualifying_order_id` assume `Order.status` is a string like
`"delivered"`/`"completed"`. Adjust to match commerce's actual order
status enum/values.

## 7. Rate limiting (Section 17)

`api/v1/reviews.py` has a comment marking where a shared rate limiter
should be injected as a dependency. If core-platform already has one
(e.g. Redis sliding window), use it there instead of adding a new one.

## 8. Frontend

Copy `frontend/app/*`, `frontend/components/discovery/*`,
`frontend/hooks/*`, `frontend/store/*`, and `frontend/lib/*` into the
main Next.js app's corresponding directories. Update:
- `NEXT_PUBLIC_API_URL` env var (or the app's existing API client) in
  `lib/api.ts` if the app already has a shared fetch wrapper — prefer
  that over this one.
- Product detail links (`/products/detail/{slug}`) to match whatever
  route the existing product detail page (owned by commerce/core-platform)
  actually uses.
- Tailwind/shadcn tokens used (`bg-background`, `text-muted-foreground`,
  etc.) assume the host app's existing design tokens — adjust class names
  if the host app's tokens differ.

## 9. What NOT to change

Per the brief: do not rewrite existing auth, product, inventory, cart,
order, or payment logic. Every touchpoint above is additive (new tables,
new routers, one hook into the existing price-update flow) — nothing here
requires modifying those systems' internals.
