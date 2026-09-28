# EVE Healthcare — Diagnostic Booking & Payment Service — Design Spec

Date: 2026-09-26
Status: Approved (design) — pending spec review
Source PRD: `assignment-brief/prd.md` (local-only, not committed)
Decisions: FastAPI, Postgres + Docker Compose, deterministic payments, full implementation, uv + Makefile

## 1. Outcome & Success Criteria

Build a small, well-tested backend that lets users discover diagnostic centres/tests, book a test, and complete a simulated payment including an idempotent webhook.

Success:
- All PRD endpoints work with correct auth/validation/codes.
- Webhook duplicate delivery causes no duplicate records or backward state transitions.
- `uv` + `Makefile` + Docker Compose one-command run; README covers setup/endpoints/schema/assumptions.
- pytest covers auth, booking guards, payment success/fail, webhook idempotency, cross-user denial.

Non-goals: real payment gateway, frontend/UI, Redis/Celery (unless time remains).

## 2. Architecture (Approach A — Layered FastAPI)

```
app/
  main.py              # app factory, router mounting, exception handlers
  core/
    config.py          # pydantic-settings (DATABASE_URL, JWT_SECRET, etc.)
    security.py        # bcrypt hashing, JWT encode/decode (python-jose)
    deps.py            # get_db, get_current_user
  models/              # SQLAlchemy 2.0 models: user, centre, test, offering, booking, payment, webhook_event
  schemas/             # Pydantic v2 request/response schemas
  routers/             # auth, centres, tests, bookings, payments, webhook
  services/            # booking_service, payment_service, webhook_service
  seed.py              # demo centres/tests/offerings
alembic/               # migrations
tests/                 # test_auth, test_bookings, test_payments, test_webhook_idempotency
Dockerfile
docker-compose.yml     # api + db
pyproject.toml + uv.lock (uv only, no pip, no requirements.txt)
Makefile               # up, dev, test, lint, migrate, seed
```

Why: separation of concerns scores maintainability; SQLAlchemy + Alembic scores DB design; service layer centralizes state-transition guards.

Rejected: (B) SQLModel lean — blurs DB/API boundary; (C) raw psycopg — manual migration burden.

## 3. Data Model

- `User(id, name, email unique, password_hash, created_at)`
- `DiagnosticCentre(id, name, location, created_at)`
- `DiagnosticTest(id, name, created_at)`
- `CentreTestOffering(id, centre_id FK, test_id FK, price NUMERIC, unique(centre_id, test_id))`
- `Booking(id, user_id FK, centre_id FK, test_id FK, appointment_datetime TIMESTAMPTZ, amount NUMERIC snapshot, status ENUM PENDING|CONFIRMED|FAILED|CANCELLED, created_at, updated_at)`
- `Payment(id, booking_id FK, status ENUM SUCCESS|FAILED, provider_reference UUID unique, created_at, updated_at)` — one-to-many allowed for retries; uniqueness on reference prevents duplicates.
- `WebhookEvent(id, event_id TEXT unique, payload JSONB, processed_at, created_at)` — idempotency ledger.

Indexes: `booking(user_id)`, `payment(booking_id)`, unique constraints as above.

## 4. API & Flows

| Method | Endpoint | Auth | Notes |
|---|---|---|---|
| POST | `/auth/signup/` | No | name, email, password → 201 |
| POST | `/auth/login/` | No | OAuth2 password form or JSON → JWT |
| GET | `/centres/` | No | list |
| GET | `/centres/{id}/` | No | detail + tests/prices via offerings |
| GET | `/tests/` | No | list, `?centre_id=` / `?location=` filter |
| POST | `/bookings/` | Yes | centre_id, test_id, appointment_datetime → validate offering exists, snapshot amount, PENDING |
| GET | `/bookings/` | Yes | own bookings only |
| GET | `/bookings/{id}/` | Yes | owner-only, 403 otherwise, 404 unknown |
| PATCH | `/bookings/{id}/cancel/` | Yes | owner-only; allowed from PENDING/FAILED only; 409 otherwise |
| POST | `/payments/` | Yes | `{booking_id, simulate: success\|fail}` deterministic; reject CANCELLED/CONFIRMED/existing SUCCESS; SUCCESS→CONFIRMED, FAILED→FAILED |
| POST | `/payments/webhook/` | No | `{event_id, provider_reference, status, booking_id?}` idempotent (see §5) |

Validation: Pydantic v2; future datetime check; consistent `{detail}` errors; codes 201/200/400/401/403/404/409.

## 5. Webhook Idempotency (Critical)

1. Lookup `WebhookEvent(event_id)` — if found, return 200 immediately (no state change).
2. Else in one DB transaction: lookup-or-create `Payment` by `provider_reference` (unique); apply forward-only transition: `PENDING|FAILED → CONFIRMED|FAILED`; never `CONFIRMED → PENDING/FAILED`; never overwrite `CANCELLED` via webhook (return 200 + record event, no transition — documented assumption).
3. Insert `WebhookEvent(event_id, payload)`; commit. Unique constraints + transaction make concurrent duplicates safe.

## 6. Auth & Security

- bcrypt (passlib) + JWT (python-jose), `Authorization: Bearer`.
- `get_current_user` dependency; owner checks on all booking/payment reads/writes.
- Webhook has no auth in MVP (PRD allows); payload must include `event_id`; signature header listed as future improvement.

## 7. Tooling (uv + Make + Docker)

- `pyproject.toml` only; `uv sync`, `uv run uvicorn app.main:app`, `uv run pytest`, `uv run alembic ...`. No pip.
- Makefile: `up` (compose up --build), `dev`, `test`, `lint` (ruff), `migrate`, `seed`, `down`.
- `docker-compose.yml`: `db` (postgres:16) + `api` (uv run uvicorn --host 0.0.0.0). Local dev can point `DATABASE_URL` at Homebrew Postgres 18.

## 8. Testing

pytest + httpx TestClient (or async client):
- signup/login + protected-route 401.
- booking create snapshots price; rejects unknown centre/test combo (400).
- list/detail isolation; cross-user 403.
- cancel guards (409 on CONFIRMED).
- payment success/fail transitions; reject CANCELLED (400/409).
- webhook: first delivery transitions; second same `event_id` → 200 no-op; same `provider_reference` different `event_id` → no duplicate payment; CONFIRMED never flips back.

## 9. Assumptions

- Cancel allowed only from PENDING/FAILED; CONFIRMED is terminal (treated as completed) — documented in README.
- Webhook never cancels; CANCELLED bookings ignore status updates (acknowledged, no transition).
- One active SUCCESS payment per booking; retries create FAILED rows only.
- Times in UTC ISO8601; price NUMERIC(10,2).

## 10. Self-Review

- No TBDs; scope is single plan-sized (MVP, no Redis/Celery/rate-limit unless bonus time).
- Consistent: deterministic `simulate` param satisfies “randomly/deterministically” PRD line; unique constraints back idempotency claims.
- No contradictions between §4/§5/§9 transition rules.

## 11. Next Step

Invoke `writing-plans` to produce the implementation plan, then implement via TDD.
