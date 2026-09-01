# feature/commerce — Commerce System

Implements the full purchasing lifecycle for Branch 2 of the platform:
Product → Cart → Checkout → Order → Payment → Payment Verification →
Inventory Finalization → Invoice → Receipt → Order History.

## Structure

```
commerce-system/
├── backend/     FastAPI + PostgreSQL + SQLAlchemy + Alembic + Redis + Celery
├── frontend/    Next.js 15 + TypeScript + Tailwind + TanStack Query + Zustand
└── docker-compose.yml   Runs db, redis, api, celery worker, celery beat, frontend
```

## IMPORTANT: core-platform dependency

`feature/core-platform` (auth, users, products, categories, brands) does
not exist yet. `backend/app/models/core_platform_stubs.py` defines the
minimal shape of those tables so this branch can run standalone. **Delete
that file and repoint the imports once core-platform lands** — see the
comment at the top of that file for the exact steps.

This also means: the initial Alembic migration (`0001_initial.py`) creates
stub `users` / `brands` / `categories` / `products` tables. Do not run this
migration against a database that already has core-platform's real tables
with the same names — pick one source of truth.

## Running locally

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
# fill in real DB/Redis URLs and gateway credentials in backend/.env

docker compose up --build
```

- API: http://localhost:8000 (docs at /docs)
- Frontend: http://localhost:3000

## Running backend tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

Tests use an in-memory SQLite DB and mock the payment gateway HTTP calls —
no real credentials or network calls are used in the test suite.

## Payment gateways

All three (bKash Tokenized Checkout, Nagad, SSLCommerz) are implemented
against their real, current API shapes (see `backend/app/payments/`) —
endpoints were verified against each provider's official developer
documentation rather than invented. Two things still need attention before
production use:

1. **Nagad's RSA signing** (`backend/app/payments/nagad.py`) has the
   correct call *shape* but the `_sign()` / `_verify_signature()` methods
   are placeholders (base64, not real RSA/SHA1 signing). Wire in the
   `cryptography` library with your actual `NAGAD_PRIVATE_KEY` /
   `NAGAD_PUBLIC_KEY` before going live — the surrounding request flow
   doesn't need to change.
2. All three providers were built from documentation, not against live
   sandbox credentials (none were provided). Run an end-to-end test against
   each gateway's sandbox before production.

## What's implemented vs. not

See `PROGRESS.md` for the section-by-section breakdown against the
original 34-section spec.
