# API Reference

Interactive docs: `http://localhost:8000/docs` (try every endpoint live).

## Endpoints

| Method | Path | Auth | Description |
| ------ | ---- | ---- | ----------- |
| GET | `/health` | no | `{"status": "ok"}` |
| POST | `/auth/signup/` | no | Register (`name`, `email`, `password`) → 201 |
| POST | `/auth/login/` | no | OAuth2 form (`username`=email) → JWT |
| GET | `/centres/` | no | List centres |
| GET | `/centres/{id}/` | no | Centre + tests with prices |
| GET | `/tests/?centre_id=&location=` | no | Offerings (test + price + centre) |
| POST | `/bookings/` | Bearer | Book a test → 201 PENDING |
| GET | `/bookings/` | Bearer | My bookings (owner only) |
| GET | `/bookings/{id}/` | Bearer | Detail (403 cross-user) |
| PATCH | `/bookings/{id}/cancel/` | Bearer | Cancel (409 if already cancelled) |
| PATCH | `/bookings/{id}/reschedule/` | Bearer | Move date, future-only (status/amount untouched) |
| POST | `/payments/` | Bearer | Pay, caller-chosen outcome (`simulate: success\|fail`) |
| POST | `/payments/mock/charge` | Bearer | Mock provider: PENDING → ~2s → 70% SUCCESS / 30% FAILED |
| POST | `/payments/webhook/` | no | Provider callback, idempotent by `event_id` |

## Curl tour

```bash
BASE=http://localhost:8000
curl -s -X POST $BASE/auth/signup/ -H 'Content-Type: application/json' \
  -d '{"name":"Asha","email":"asha@example.com","password":"secret123"}'
TOKEN=$(curl -s -X POST $BASE/auth/login/ \
  -d 'username=asha@example.com&password=secret123' | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
AUTH="Authorization: Bearer $TOKEN"
curl -s $BASE/centres/
curl -s -X POST $BASE/bookings/ -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"centre_id":1,"test_id":1,"appointment_datetime":"2026-10-01T10:00:00Z"}'
curl -s -X POST $BASE/payments/mock/charge -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"booking_id":1}'
# webhook replay: same event twice → second is a no-op ack (same 200, no new rows)
curl -s -X POST $BASE/payments/webhook/ -H 'Content-Type: application/json' \
  -d '{"event_id":"evt-1","provider_reference":"ref-1","status":"SUCCESS","booking_id":1}'
curl -s -X PATCH $BASE/bookings/1/cancel/ -H "$AUTH"
```

## Error contract

Every error is `{detail}` with the right code:

| Code | Meaning | Examples |
| ---- | ------- | -------- |
| 400 | Bad input | past date, cancelled booking payment, bad webhook status |
| 401 | No/bad token | missing `Authorization` header |
| 403 | Authenticated but forbidden | another user's booking, non-admin on `/admin/*` |
| 404 | Unknown id | booking/centre/test/payment not found |
| 409 | Illegal state transition | double-pay, cancel cancelled, delete referenced row |
| 422 | Schema violation | wrong types, blank webhook ids, bad price |
