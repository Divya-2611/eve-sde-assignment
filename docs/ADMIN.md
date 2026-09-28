# Admin Panel

Ops backend + UI. **No money movement** — admin never creates/refunds
payments or changes booking status; catalogue writes only.

## Setup

```bash
# .env — either path works:
ADMIN_EMAILS=admin@example.com            # allowlist (grant at signup/login)
# or bootstrap a login-ready admin with no signup step:
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-me-admin
make up && make seed-docker               # seed creates the admin user
# log in as admin@example.com → /admin unlocks
```

Rights come from the comma-separated allowlist, matched case-insensitively:
granted at signup, reconciled both ways at login (removing an email demotes
on next login). Changing the list needs no migration.

## Endpoints (admin JWT; else 401/403)

| Method | Path | Description |
| ------ | ---- | ----------- |
| GET | `/admin/bookings?status=&centre_id=&user=&limit=&offset=&order=` | All bookings with owner email + names. `limit` default 50, max 200 |
| GET | `/admin/bookings/stats?...` | Same filters: `total`, per-status `counts`, `confirmed_sum` |
| GET | `/admin/tests` | All tests, including zero-offering ones |
| GET | `/admin/payments?booking_id=&limit=&offset=` | All payments |
| POST/PATCH/DELETE | `/admin/centres[/{id}]` | CRUD (409 if referenced) |
| POST/PATCH/DELETE | `/admin/tests[/{id}]` | CRUD (409 if referenced) |
| PUT | `/admin/offerings` | Price upsert (404 unknown, 422 bad price) |

```bash
ADMIN_AUTH="Authorization: Bearer <admin-jwt>"
curl -s "$BASE/admin/bookings?limit=5" -H "$ADMIN_AUTH"
curl -s -X PUT $BASE/admin/offerings -H "$ADMIN_AUTH" -H 'Content-Type: application/json' \
  -d '{"centre_id":1,"test_id":1,"price":"199.00"}'
```

## UI (`/admin`)

| Route | Page |
| ----- | ---- |
| `/admin` | Dashboard: status counts + CONFIRMED revenue + latest 10 |
| `/admin/bookings` | Filterable read-only bookings table |
| `/admin/catalogue` | Centres/tests CRUD + price editor |

Non-admins see an inline 403 panel (no redirect loop). Nav entry appears
only for admins. The UI guard is display-only — `require_admin` on the
backend is the real enforcement.
