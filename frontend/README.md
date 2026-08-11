# AccessCore Frontend

Next.js (App Router) admin console for the AccessCore IAM platform. Consumes
the FastAPI backend in `../backend` — no business logic is duplicated here;
every permission check shown in the UI is a courtesy, not a security
boundary, and the backend re-validates everything on every request.

## Stack

- Next.js 16 (App Router, Turbopack)
- TypeScript (strict)
- Tailwind CSS v4
- shadcn/ui (built on Base UI)
- Vitest + React Testing Library

## Getting started

```bash
cp .env.local.example .env.local
npm install
npm run dev
```

Requires the backend running locally (see `../backend/README.md` or the
repo root `docker-compose.yml`) at the URL configured in `.env.local`.

## Architecture

```
app/
├── login/                  public login page
├── dashboard/              authenticated app shell + pages
│   ├── layout.tsx          sidebar/topbar, client-side auth guard
│   ├── users/roles/permissions/audit-logs/
└── api/auth/                Route Handlers acting as a BFF for the auth
                              flow only (login/refresh/logout) - the only
                              place the refresh token cookie is touched

lib/
├── api/                    typed API client (one module per resource)
├── session-store.ts        in-memory session (access token, user, permissions)
└── server/                 server-only helpers used by the BFF routes

components/
├── ui/                     shadcn primitives
├── layout/                 sidebar, topbar, nav
├── permission-gate.tsx     UX-only permission gating
└── <resource>/             per-resource tables, forms, dialogs

proxy.ts                    coarse auth gate (redirects based on cookie
                             presence only - real validation happens
                             client-side via SessionProvider)
```

### Token handling

- Access token: in-memory only (`lib/session-store.ts`), never persisted.
  Gone on tab close/reload by design.
- Refresh token: httpOnly cookie, set only by the `/api/auth/*` route
  handlers. Client-side JS never sees it.
- Concurrent 401s collapse into a single `/api/auth/refresh` call
  (`lib/api/token-refresh.ts`) since the backend's refresh tokens are
  single-use/rotating — two independent refresh calls would race.

See the root `README.md` for the full security rationale.

## Testing

```bash
npm run test        # Vitest + React Testing Library
npm run lint         # ESLint
npx tsc --noEmit     # TypeScript
npm run build        # production build
```
