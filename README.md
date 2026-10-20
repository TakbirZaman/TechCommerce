# TechCommerce

A full-stack e-commerce platform built with **FastAPI** + **Next.js** featuring AI-powered product recommendations, PC Builder with compatibility checking, and a product comparison engine.

---

## Features

### Storefront
- **Product Catalog** — 90 source-linked products across 15 categories with verified model photos and listed specifications
- **Search & Autocomplete** — Instant product search with real-time suggestions
- **Product Reviews** — Star ratings and written reviews on every product
- **Guest Checkout** — Buy without creating an account
- **User Accounts** — Register, login, view order history

### Smart Tools
- **AI Advisor** — Describe what you need in plain English, get product recommendations
- **Comparison Engine** — Add products to compare side-by-side (specs, price, winner)
- **PC Builder** — Pick components, get real-time compatibility checks and pricing

### Admin Panel (`/admin`)
- **Dashboard** — Revenue, orders, users, low stock alerts
- **Products** — CRUD with image upload, search, pagination
- **Orders** — Filter by status, update order/payment status
- **Coupons** — Percentage or flat discount codes with expiry
- **Customers** — View registered users, search by name/email
- **Delivery Zones** — Set delivery fees per city/area

### Commerce
- **Session-based Cart** — Works for guests and logged-in users
- **Coupon System** — Apply discount codes at checkout
- **Order Tracking** — Track order status with order number + email

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.14, FastAPI, SQLAlchemy 2.0, Pydantic v2 |
| Database | SQLite (ships with the project, no setup needed) |
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS |
| Icons | Lucide React |
| Auth | JWT (HMAC-signed tokens) |

---

## Prerequisites

You need these installed on your machine:

- **Python 3.10+** — [python.org](https://www.python.org/downloads/)
- **Node.js 18+** — [nodejs.org](https://nodejs.org/)
- **Git** — [git-scm.com](https://git-scm.com/)

---

## Quick Start (3 steps)

### 1. Clone the repo

```bash
git clone https://github.com/TakbirZaman/TechCommerce.git
cd TechCommerce
```

### 2. Install dependencies

```bash
# Python dependencies
pip install -r requirements.txt

# Frontend dependencies
cd frontend
npm install
cd ..
```

### 3. Seed the database & run

```bash
# Install sourced products, specifications and local photos
python scripts/seed.py

# Start the backend (port 8000)
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# In a NEW terminal — start the frontend (port 3000)
cd frontend
npm run dev
```

### Open in your browser

| Page | URL |
|------|-----|
| **Storefront** | http://localhost:3000 |
| **Admin Panel** | http://localhost:3000/admin |
| **API Docs (Swagger)** | http://localhost:8000/docs |
| **API Docs (ReDoc)** | http://localhost:8000/redoc |

---

## Initial administrator

Before seeding a new deployment, set `SEED_ADMIN_EMAIL` and
`SEED_ADMIN_PASSWORD` in your environment. Use a unique password of at least
12 characters. Without both values, the catalog is installed and admin creation
is skipped. Existing admin accounts and passwords are left unchanged.

Guest checkout works without login — fill in name, phone, email, and address at checkout.

---

## Project Structure

```
TechCommerce/
├── main.py                  # FastAPI app entry point
├── core/
│   ├── database.py          # SQLAlchemy engine + session
│   ├── models/
│   │   ├── specification.py # Product, Spec templates, Reviews
│   │   ├── commerce.py      # Cart, Order, Payment, Coupon
│   │   └── advisor.py       # AI recommendation models
│   └── routers/
│       ├── auth.py          # Register, login, profile
│       ├── catalog.py       # Products, search, reviews
│       ├── commerce.py      # Cart, checkout, orders
│       ├── comparison.py    # Product comparison
│       ├── pc_builder.py    # PC Builder + compatibility
│       ├── advisor.py       # AI advisor
│       └── admin.py         # Admin CRUD + upload
├── scripts/
│   ├── seed.py              # Database seeding
│   └── import_icecat.py     # Icecat product importer
├── frontend/
│   └── src/
│       ├── app/             # Next.js pages (App Router)
│       │   ├── page.tsx           # Homepage
│       │   ├── products/          # Product listing + detail
│       │   ├── cart/              # Shopping cart
│       │   ├── checkout/          # Checkout flow
│       │   ├── compare/           # Comparison view
│       │   ├── pc-builder/        # PC Builder
│       │   ├── advisor/           # AI advisor
│       │   ├── search/            # Search results
│       │   ├── login/             # User login
│       │   ├── register/          # User registration
│       │   ├── account/           # User account
│       │   ├── track-order/       # Order tracking
│       │   └── admin/             # Admin panel
│       ├── components/layout/    # Navbar, Footer
│       └── lib/api.ts             # API client
├── uploads/products/        # Product images
└── techcommerce.db          # SQLite database
```

---

## API Endpoints

### Public
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/catalog/products` | List products |
| GET | `/api/v1/catalog/products/{slug}` | Product detail |
| GET | `/api/v1/catalog/search?q=` | Search products |
| GET | `/api/v1/catalog/autocomplete?q=` | Search suggestions |
| GET | `/api/v1/catalog/products/{slug}/reviews` | Get reviews |
| POST | `/api/v1/catalog/products/{slug}/reviews` | Submit review |
| POST | `/api/v1/commerce/cart/items` | Add to cart |
| GET | `/api/v1/commerce/cart` | View cart |
| POST | `/api/v1/commerce/checkout` | Place order |
| POST | `/api/v1/commerce/orders/track` | Track order |
| POST | `/api/v1/compare/add` | Add to comparison |
| GET | `/api/v1/compare/current` | View comparison |
| POST | `/api/v1/pc-builder/check-compatibility` | Check build |
| POST | `/api/v1/advisor/recommend` | Get AI advice |

### Auth Required
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | Login |
| GET | `/api/v1/auth/me` | Current user |

### Admin Required
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/dashboard` | Dashboard stats |
| GET/POST | `/api/v1/admin/products` | List / create products |
| PUT/DELETE | `/api/v1/admin/products/{id}` | Update / delete product |
| GET/PUT | `/api/v1/admin/orders` | List / update orders |
| GET/POST | `/api/v1/admin/coupons` | List / create coupons |
| PUT | `/api/v1/admin/coupons/{id}` | Update coupon |
| GET | `/api/v1/admin/users` | List users |
| GET/POST | `/api/v1/admin/delivery-zones` | List / create zones |
| PUT | `/api/v1/admin/delivery-zones/{id}` | Update zone |
| POST | `/api/v1/admin/upload-image` | Upload product image |
| DELETE | `/api/v1/admin/images/{id}` | Delete image |

---

## Product data and photos

Normal seeding loads the checked-in `data/catalog.json` snapshot without network
requests. It contains 90 product listings across all 15 categories, with BDT
reference prices observed on 20 October 2026, factual listing specifications,
source product/image URLs, capture timestamps, and SHA-256 photo checksums.
Model-matched 500 × 500 photographs are bundled as optimized WebP files in
`uploads/products/catalog/`; pages use uncropped product-image sizing.

Source: [Star Tech](https://www.startech.com.bd/). Product images retain their
original owners' rights; source links are retained for attribution and review.
Prices are dated reference observations, not a live feed. No reviews, orders,
sales counts, discounts, or warehouse quantities are invented by this seed.
New products start with zero warehouse stock: set your selling prices and actual
stock in **Admin → Products** before taking orders. Existing operator prices,
stock, status and uploaded galleries survive repeated seeding.

Running `python scripts/seed.py` on an older database retires recognizable demo
products that still have only category placeholders. It keeps their database
rows and order history, and preserves products with operator-uploaded photos.
Back up an existing database before any catalog migration.

To capture a new snapshot manually (requires network access):

```bash
python scripts/refresh_catalog.py --per-category 6
python scripts/seed.py
```

The refresh refuses to replace the snapshot if any category is missing. Existing
products' selling prices are deliberately preserved by the seed; review the new
reference prices in `data/catalog.json` and update selling prices in Admin.

---

## Troubleshooting

**Port already in use**
```bash
# Kill existing processes on port 8000/3000
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**Database issues — reset everything**
```bash
del techcommerce.db
python scripts/seed.py
```

**Frontend not loading**
```bash
cd frontend
npm install
npm run dev
```

**Backend import errors**
```bash
pip install -r requirements.txt
```

---

## License

MIT
