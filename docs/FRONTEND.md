# Frontend

React + Vite + TypeScript SPA in `frontend/` (react-router-dom, no component
library). Demo companion to the API.

## Setup

```bash
npm --prefix frontend install
make web            # dev server :5173 → VITE_API_URL (default :8000)
make web-build      # production build (tsc + vite)
docker compose --profile web up --build   # nginx :3000 (default up unchanged)
```

`VITE_API_URL` is baked at **build** time — rebuild after changing it.

## Routes

| Route | Auth | Page |
| ----- | ---- | ---- |
| `/` | no | Centre catalogue |
| `/centres/:id` | no | Detail + tests/prices + book |
| `/signup`, `/login` | no | Register / login (`?next=` redirect) |
| `/bookings` | yes | My bookings: pay, cancel (+refund note if paid), reschedule |
| `/checkout/:bookingId` | yes | Mock provider checkout (2s PENDING → result) |
| `/admin/*` | admin | Dashboard, bookings table, catalogue manager |

JWT lives in `localStorage` (`eve_jwt`); any 401 clears it and redirects to
`/login?next=...`.

## Smoke checklist

1. `npm --prefix frontend run build` — PASS, no TS errors.
2. Signup → login → JWT stored; centres list + detail with prices.
3. Book (future datetime) → checkout → Proceed to Payment → CONFIRMED/FAILED.
4. Cancel from `/bookings` (refund note on paid); reschedule moves the date.
5. Direct-load `/bookings` — no 404 (nginx SPA fallback).
6. Logged-out `/bookings` → `/login?next=/bookings`.
