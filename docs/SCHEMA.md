# Schema, Assumptions, Future Work

## Data model

```
users ──< bookings >── centres ──< offerings >── tests
               │                        (uq centre_id+test_id)
               └─< payments (uq provider_reference)
                        └── webhook_events (uq event_id)
```

- `offerings.price` is **per-centre** (same test, different price per lab).
- `bookings.amount` snapshots the price at booking time.
- `centres.location` indexed; `tests.name` unique.
- Money `NUMERIC(10,2)` end to end; datetimes UTC (ISO-8601 `Z`).
- Migrations: `alembic/versions/` (`alembic upgrade head` / `alembic check`).

## Assumptions

- Cancel works on `PENDING`/`FAILED`/`CONFIRMED`; paid cancels keep the
  payment row (UI shows a refund note; no automatic refund processing).
- Webhook never moves state backwards: `CONFIRMED` never regresses,
  `CANCELLED` is acknowledged without transition; repeats are no-ops.
- One `SUCCESS` payment per booking (409 on double-pay; retries are new attempts).
- Webhook endpoint carries no auth (provider callbacks can't log in);
  HMAC verification is future work (below).

## Future work (with more time)

- Real gateway (Razorpay/Stripe) + HMAC-signed webhooks
- Refresh tokens, password reset, per-user rate limiting
- Partial unique index for one-SUCCESS-per-booking
- Refund processing, reschedule blackout window
- Structured logging, `alembic check` in CI
