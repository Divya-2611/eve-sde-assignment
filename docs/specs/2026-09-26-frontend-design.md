# EVE Healthcare Frontend — Design Spec

Date: 2026-09-26
Status: Approved (design) — pending spec review
Backend: FastAPI service on `master` (auth, centres/tests, bookings, payments, webhook)
Decisions: full product UI, React + Vite SPA in `frontend/`, full flow, full build

## 1. Outcome & Success Criteria

A polished browser UI that demos the complete backend flow without curl:
signup/login → browse centres/tests → book → pay (simulated) → manage bookings (cancel).

Success:
- All six routes work against a running backend with correct auth behavior.
- JWT session persists across reloads; 401s redirect to login.
- Backend `{detail}` errors surface as user-readable messages.
- `npm run build` passes (TypeScript strict); dev runs alongside backend.
- Backend remains untouched (no API changes; no backend image coupling).

Non-goals: admin views, webhook tester, SSR, component library, i18n.

## 2. Architecture (Approach A — Standalone Vite SPA)

```
frontend/
  package.json            # react, react-router-dom, vite, typescript
  vite.config.ts          # dev proxy /api -> localhost:8000 (optional), base ./
  index.html
  src/
    main.tsx              # router mount
    api.ts                # single API client (see §4)
    auth.tsx              # AuthProvider + useAuth + ProtectedRoute
    pages/
      Login.tsx Signup.tsx Centres.tsx CentreDetail.tsx
      Bookings.tsx Checkout.tsx
    components/
      StatusPill.tsx ErrorBanner.tsx Layout.tsx
    styles.css            # design tokens + responsive layout
```

Why: backend stays a pristine submission artifact; Vite SPA is the standard
review-friendly stack with the fastest setup. Rejected: (B) serving dist/
from FastAPI — couples builds; (C) Next.js — SSR overkill for an API demo.

## 3. Routes & Flows

| Route | Access | Content |
|---|---|---|
| `/signup` | public | name, email, password → POST /auth/signup/ → redirect login |
| `/login` | public | email, password (form-encoded, mirrors backend OAuth2 form) → JWT → `/` |
| `/` | public | centres list + text/location filter (client-side over GET /centres/) |
| `/centres/:id` | public | detail + tests/prices (GET /centres/{id}/) + datetime picker + Book button (auth-gated: prompts login) |
| `/bookings` | protected | own bookings (GET /bookings/): status pills, Pay (→ checkout) and Cancel (confirm dialog → PATCH cancel) actions per valid state |
| `/checkout/:bookingId` | protected | amount summary + Success/Fail toggle (mirrors `simulate` param) → POST /payments/ → result view linking back to /bookings |

Guards: `ProtectedRoute` redirects unauthenticated users to `/login?next=...`;
booking actions render only for valid states (Pay for PENDING/FAILED, Cancel
for PENDING/FAILED) matching backend 409 rules.

## 4. API Client (`api.ts`)

- `const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000"`.
- `signup(name,email,password)`, `login(email,password)` (URLSearchParams
  username/password), `listCentres()`, `centreDetail(id)`,
  `listTests(params?)`, `createBooking({centre_id,test_id,appointment_datetime})`,
  `myBookings()`, `bookingDetail(id)`, `cancelBooking(id)`,
  `payBooking(bookingId, simulate: "success"|"fail")`.
- `request()` helper: attaches `Authorization: Bearer <token>` from
  localStorage (`eve_jwt`), parses JSON, throws `ApiError(message)` from
  `{detail}` (string or array) with status attached.
- `AuthProvider`: login/logout/signup, token persistence, `authFetch`
  that clears session + redirects on 401.

## 5. UX & Styling

- Design tokens in `styles.css`: `--bg, --card, --accent, --danger, --muted`,
  radius, spacing scale. No component library.
- `StatusPill`: color per status (PENDING amber, CONFIRMED green,
  FAILED red, CANCELLED gray).
- `ErrorBanner`: renders `ApiError.message`; inline field errors where
  applicable.
- Datetime input `min` set to now (future-only, mirroring backend guard).
- Responsive: single column <720px, two-column grids above.
- Copy: product tone ("Book a test", "Your bookings"), prices as ₹ with
  2 decimals from API values (display only, no arithmetic).

## 6. Tooling

- Node toolchain (npm) for frontend; backend stays uv-only.
- `vite.config.ts`: `server.proxy` `/api → http://localhost:8000` optional
  convenience; client defaults to absolute `VITE_API_URL`.
- `Makefile` gains: `web` (`npm --prefix frontend run dev`),
  `web-build` (`npm --prefix frontend run build`), `web-preview`.
- `docker-compose.yml` gains optional `web` service (nginx:alpine serving
  `frontend/dist/`, `VITE_API_URL` baked at build) — profile-gated so
  default `make up` is unchanged.
- TypeScript `strict: true`; `npm run build` runs `tsc && vite build`.

## 7. Testing

- Smoke checklist (manual, documented in README section): signup, login,
  centres filter, book future slot, pay success → CONFIRMED pill, pay fail
  → FAILED pill, cancel PENDING → CANCELLED, cross-check owner isolation
  (second user sees no bookings), past-date blocked client-side.
- No JS unit-test harness in MVP (documented follow-up: vitest for api.ts
  error mapping + guards).

## 8. Assumptions

- Backend runs at `VITE_API_URL` with CORS allowing the dev origin; if the
  backend blocks cross-origin dev requests, add `fastapi.middleware.cors`
  origins as a minimal backend patch (documented, opt-in).
- Currency display only; amounts authoritative from booking responses.
- Session = localStorage JWT (demo-appropriate; httpOnly cookies listed as
  hardening follow-up).

## 9. Self-Review

- No TBDs; single-plan scope (6 pages, 1 client, styles, tooling).
- Consistent: route guards mirror backend 401/403/409 rules; `simulate`
  toggle matches deterministic payment contract; money display-only matches
  backend NUMERIC ownership.
- No contradictions with backend spec; frontend introduces no API changes.

## 10. Next Step

Invoke `writing-plans` to produce the implementation plan, then implement.
