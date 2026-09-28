# EVE Healthcare Admin Panel — Design Spec

Date: 2026-09-26
Status: Approved (design) — pending spec review
Decisions: full ops panel, API + React UI, `is_admin` role flag (Approach A)

## 1. Outcome & Success Criteria

Ops-grade admin layer over the existing booking service: admins see every
booking/payment across users and manage the catalogue (centres, tests,
per-centre prices) from API + UI.

Success:
- Non-admins get 403 on every `/admin/*` route (API + UI gate).
- Admin can list/filter all bookings and payments with owner context.
- Admin can CRUD centres/tests and upsert offering prices without breaking
  the booking flow's guards.
- `pytest` green, `npm run build` green, migration upgrades cleanly.
- No money movement via admin (payments stay user-flow + webhook only).

Non-goals: refunds/chargebacks, user management (suspend/delete), analytics
charts, audit log (listed as follow-ups).

## 2. Architecture (Approach A — Native Admin Layer)

```
app/
  models/user.py        # + is_admin column
  core/deps.py          # + require_admin()
  core/security.py      # JWT gains is_admin claim (default False)
  routers/admin.py      # all /admin/* endpoints (new)
  services/admin_service.py  # catalogue writes reusing offering validation
alembic/versions/*_admin_flag.py
frontend/src/pages/admin/
  Dashboard.tsx Bookings.tsx Catalogue.tsx
frontend/src/main.tsx   # /admin/* routes behind admin guard + nav entry
```

Rejected: (B) sqladmin — bypasses service guards, heavy dep, no React UI;
(C) separate admin service — double deploy/auth for this size.

## 3. Data & Access Control

- `users.is_admin BOOLEAN NOT NULL DEFAULT FALSE` + Alembic migration
  (default keeps existing rows non-admin; index not required).
- Bootstrap: `ADMIN_EMAILS` env (comma-separated). Matching email is granted
  `is_admin=True` at signup, and reconciled at login (so pre-existing users
  can be promoted without DB surgery). Documented in README + `.env.example`.
- `require_admin()` FastAPI dependency: 401 unauthenticated, 403
  authenticated-but-not-admin, both `{detail}` envelope.
- JWT `is_admin` claim (default False for old tokens); frontend reads it for
  nav gating, backend re-checks from DB per request (token claim ishint,
  DB is authority — revocation-safe).

## 4. Admin API (`/admin/`, all admin-only)

| Method | Endpoint | Notes |
|---|---|---|
| GET | `/admin/bookings?status=&centre_id=&user=` | all users; each row joins user email + centre/test names; paginated (`limit`/`offset`, default 50); `order=asc\|desc` by id; aggregates via `GET /admin/bookings/stats` (same filters) |
| GET | `/admin/payments?booking_id=` | with booking ref + provider_reference + status; paginated (`limit`/`offset`, default 50, max 200) |
| GET | `/admin/tests` | all tests including tests with zero offerings (drives admin catalogue table + offering dropdown) |
| POST | `/admin/centres` | `{name, location}` → 201 |
| PATCH/DELETE | `/admin/centres/{id}` | DELETE 409 if offerings/bookings reference it |
| POST | `/admin/tests` | `{name}` → 201 |
| PATCH/DELETE | `/admin/tests/{id}` | DELETE 409 if referenced |
| PUT | `/admin/offerings` | `{centre_id, test_id, price}` upsert; 404 unknown centre/test; price > 0 else 422 |

Catalogue writes go through `admin_service` reusing the same
offering-existence/price rules as booking creation. No POST /admin/payments,
no booking status override (state machine stays user/webhook-driven).

## 5. Admin UI (`/admin/*`, admin-gated)

- Route guard: non-admin sees 403 page (not redirect loop); nav shows
  "Admin" entry only when `is_admin`.
- `/admin` dashboard: count cards per booking status + sum of CONFIRMED
  amounts (display only) + recent bookings table (latest 10).
- `/admin/bookings`: full table (id, user email, centre, test, amount,
  status pill, appointment) + status/centre filters. Read-only table —
  no checkout links and no pay/cancel actions (user-owned); a booking's
  payments are inspected via `GET /admin/payments?booking_id=`.
- `/admin/catalogue`: centre list with inline add/edit; per-centre test
  table with price editor (upsert) + add-test form; delete with 409
  surfacing ("in use").
- Same CSS system (`styles.css` additions: `table`, `toolbar`, `stat-cards`);
  no new frontend deps.

## 6. Testing

Backend pytest (new `tests/test_admin.py`):
- non-admin JWT → 403 on every admin route; no token → 401.
- admin bookings list shows other users' rows with emails.
- centre/test CRUD round-trip; delete referenced → 409.
- offering upsert creates then updates price; bad centre → 404.
- admin login JWT carries `is_admin=True`; old-claim-less token treated
  as non-admin.
- Full suite stays green (no regressions in user flows).

Frontend: `npm run build` PASS + live smoke checklist (README): admin login
sees nav entry, dashboard counts, price edit reflects in catalogue.

## 7. Assumptions

- Single `is_admin` boolean (no RBAC tiers) — enough for ops demo.
- `ADMIN_EMAILS` reconciliation at login means demotion also propagates
  (removed email loses flag on next login).
- Admin reads are eventually consistent with user writes (same DB, no cache).
- Money display only; amounts authoritative from booking rows.

## 8. Self-Review

- No TBDs; single-plan scope (flag + guard + router + service + 3 pages).
- Consistent: 403/409/404 codes match existing envelope; catalogue rules
  reuse booking-service validation; JWT claim defaults keep old tokens valid.
- No user-flow behavior changes; admin adds endpoints, alters none.

## 9. Next Step

Invoke `writing-plans` to produce the implementation plan, then implement.
