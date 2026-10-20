# Vercel API deployment

The `techcommerce-api` project deploys the Python API from the repository root.
It is separate from the Next.js storefront in `frontend/`.

## Project settings

- Root Directory: repository root (leave the field empty).
- Framework Preset: FastAPI. The root `vercel.json` also pins this preset,
  overriding the mistaken Services preset that caused the missing-services error.
- Build Command: leave the override disabled; the root config explicitly disables
  a build command so the root npm script cannot build the Next.js storefront.
- Entrypoint: `app.py`, which re-exports the existing `main.app` ASGI application.
- Set `DATABASE_URL` to an external PostgreSQL database and configure
  `JWT_SECRET_KEY`, `FRONTEND_URL`, and any required application secrets in Vercel.
  Local SQLite files and uploaded files are not durable Vercel storage.

For a separate storefront project, use Root Directory `frontend` and Framework
Preset Next.js. Its existing `frontend/vercel.json` proxies the API to Render;
changing API hosts requires deliberately updating those destinations.

## Validation limits

This change fixes the reported configuration mismatch. It has not been tested
with a Vercel build because the execution workspace and Vercel account controls
are unavailable in this session. Check the new preview deployment's build log.

The catalog PR already records missing backend imports, including
`core.middleware.rate_limit`, `InventoryTransactionType`, and
`core.services.inventory_service`. Those can still prevent the application from
starting after the framework configuration passes. A successful configuration
step is not evidence of a healthy running API.

Official references:
- https://vercel.com/docs/project-configuration/vercel-json
- https://vercel.com/docs/frameworks/backend/fastapi
