# EVE Healthcare — Diagnostic Booking & Payment Service

Backend (FastAPI + Postgres) for booking diagnostic tests at lab centres,
with simulated payments and an idempotent payment webhook. Includes a React
demo UI and an ops admin panel. Built as an SDE Intern assignment.

## Quickstart

Prerequisites: [uv](https://docs.astral.sh/uv/), Docker, Python 3.12, Node 20.

```bash
cp .env.example .env
make up               # db (:5432) + api (:8000); migrates on boot
make seed-docker      # demo centres / tests / prices
make web              # frontend (:5173)
make test             # 53 pytest, hermetic — no DB needed
```

Interactive API: `http://localhost:8000/docs`

## Docs

- [`docs/API.md`](docs/API.md) — endpoints, curl tour, error contract
- [`docs/ADMIN.md`](docs/ADMIN.md) — ops panel setup + reference
- [`docs/FRONTEND.md`](docs/FRONTEND.md) — SPA routes, env, smoke checklist
- [`docs/SCHEMA.md`](docs/SCHEMA.md) — data model, assumptions, future work

## Layout

```
app/core/      config, DB, auth guards, JWT
app/models/    7 tables (users → bookings → payments)
app/routers/   auth, bookings, payments, catalog, admin
app/services/  business rules (booking, payment, admin)
app/seed.py    demo data        alembic/       migrations
tests/         53 pytest        frontend/      React + Vite SPA
```
