# feature/commerce — Final Progress Report

Tracked against the 34-section BRANCH 2 MASTER PROMPT.

## ✅ Implemented

- **1-2 Scaffolding**: FastAPI + SQLAlchemy + Alembic + Docker Compose (db, redis, api, celery worker, celery beat, frontend), Dockerfiles, .env templates.
- **3 Never trust the client**: enforced throughout — cart/checkout schemas have no price/total fields; every price/stock check re-reads the DB row.
- **4-5 Cart**: full CRUD, stock validation, row-locking for race safety, duplicate-add accumulates quantity. Tests in `tests/test_cart.py`.
- **6 Checkout**: server-side subtotal/discount/delivery/total recalculation in `checkout_service.py`. Tests in `tests/test_checkout.py`.
- **7 Order/OrderItem models**: price snapshotted at purchase time, never recomputed from live Product.price.
- **8 Order numbers**: `ORD-YYYY-NNNNNN`, race-safe via row-locked counter table (portable Postgres/SQLite). Uniqueness tested.
- **9 Order status state machine**: fixed allow-listed transition graph in `order_state_machine.py`; illegal jumps (e.g. DELIVERED→PAYMENT_PENDING) rejected and tested.
- **10 Inventory reservation**: reserve/release/finalize with `SELECT...FOR UPDATE`, in `inventory_service.py`. Tested in `tests/test_inventory.py`.
- **11 Payment abstraction**: `PaymentProvider` ABC; order/checkout services never import gateway code directly — only `payment_service.py` does.
- **12 Payment model**: all required fields + status enum.
- **13-15 bKash/Nagad/SSLCommerz**: real endpoint shapes (verified via each provider's official docs, not invented). Nagad's RSA signing is a documented placeholder — see README.
- **16-17 Idempotency + callback security**: `ProcessedCallback` dedupe table checked before any side effect; every callback re-verified server-side against the gateway, never trusted from payload alone. Tested in `tests/test_payment_idempotency.py` (success, duplicate, failure, amount-mismatch cases).
- **18-19 Payment failure/success flows**: failure releases reservation; success finalizes inventory, queues invoice + notification via Celery.
- **20-21 Invoice**: ReportLab PDF generation with all required fields; storage abstraction over S3/R2 (`storage_service.py`), metadata-only in Postgres, signed download URLs.
- **22 Customer order history**: `GET /orders`, `GET /orders/{id}` — ownership enforced in the query itself (IDOR-safe).
- **23 Admin order management**: list/view/update-status endpoints; PAID is deliberately not admin-settable (must go through verified payment).
- **24 Delivery info snapshot**: immutable shipping fields stored directly on Order.
- **25-28 Frontend**: `/cart`, `/checkout` (3-step wizard), `/order-success`, `/orders`, `/orders/[id]` — all built with TanStack Query, Zustand (UI state only, no money values), React Hook Form + Zod. Order-success polls backend for real payment status rather than trusting the redirect.
- **29 Celery**: invoice generation, notifications, and two reconciliation/cleanup jobs (stale PAYMENT_PENDING sweep, missing-invoice sweep) on a beat schedule.
- **30 Notifications**: `notification_service.py` foundation — routes/services call it, not raw email logic; no concrete provider (SES/SendGrid) wired up yet.
- **31 Security**: IDOR protection on customer order/invoice endpoints (ownership filtered in the query), admin endpoints behind `require_admin`, payment callbacks signature/shape-checked + idempotent.
- **32 Testing**: cart CRUD, checkout calculation, order state machine, inventory reserve/release/finalize, payment success/duplicate/failure/amount-mismatch — all in `backend/tests/`.

## ⚠️ Known gaps / needs attention before production

- **Tests are unrun.** This sandbox has no network access to `pip install` or `npm install`, so nothing here has executed against a real interpreter/DB — only `python3 -m py_compile` (syntax) was verified for the backend. Run `pytest tests/ -v` yourself before trusting this.
- **Nagad RSA signing is a placeholder** (see README) — base64 stand-in, not real PKCS1v15/SHA1 signing.
- **No real credentials tested** against any gateway's sandbox — all three were built from documentation.
- **Discount codes**: the checkout service has a seam (`_calculate_discount`) but no real promotions table exists (correctly out of scope per Section 33, but flagging the seam).
- **Delivery charge** is a flat ৳60 placeholder — no shipping-zone table exists yet.
- **Frontend has no automated tests** (Section 32 focuses on backend; none were requested for frontend, none were written).
- **Auth**: `core-platform` doesn't exist, so `app/core/security.py` verifies JWTs against an assumed claim shape (`sub`, `role`, `email`). Confirm this matches core-platform's actual token format once that branch exists.
- **Email/SMS notifications** are logging stubs only — no SES/SendGrid/Twilio wired in.

## Not implemented (explicitly out of scope per Section 33)

ML recommendations, AI advisor, advanced comparison, Elasticsearch, advanced review system.
