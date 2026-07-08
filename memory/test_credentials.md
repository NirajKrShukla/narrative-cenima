# AiPillu Studio — Test Credentials

Last updated: 2026-07-07 (auth rollout)

## Seeded Admin (auto-created on backend startup)

- **Email**: `admin@aipillu.studio`
- **Password**: `aipilluAdmin@2026`
- **Role**: `admin`
- **Auth provider**: `email` (JWT)
- Notes: Admin bypasses per-project ownership checks. The password is (re)hashed
  automatically on every backend startup from `ADMIN_PASSWORD` in
  `/app/backend/.env`. `test_credentials.md` is the single source of truth for
  the current live password.

## Authentication endpoints

All auth routes live under `/api/auth`:

| Method | Path | Purpose |
| ------ | ---- | ------- |
| POST | `/api/auth/register` | Email + password signup → sets `access_token` + `refresh_token` httpOnly cookies |
| POST | `/api/auth/login` | Email + password login |
| POST | `/api/auth/logout` | Clears all auth cookies + deletes emergent session |
| GET  | `/api/auth/me` | Returns the current user (401 if guest) |
| POST | `/api/auth/refresh` | Refreshes the `access_token` cookie using `refresh_token` |
| POST | `/api/auth/session` | Emergent-managed Google auth exchange (`session_id` → `session_token` cookie) |

## Gating summary

- **Public** (no login): landing page `/`, demo videos via `/api/storage/demo_*.mp4`, health, Stripe webhook, voice previews.
- **Protected** (login required):
  - `/studio`, `/studio/:pid` — creating and managing films
  - `/gallery`, `/gallery/:pid` — browsing published films
  - `/api/projects/*` — every project route (auth + per-project ownership enforced by middleware)
  - Film download and social share URLs
- **Free unlock**: 1 free film ≤ 20 MB **per user email** (was per-browser via localStorage before this rollout).

## Emergent Google Auth (test identity)

- Redirect URL: `${window.location.origin}/auth/callback`
- No app-managed password — Google identities are looked up by `email` and merged
  into the same `users` collection as email/password accounts (`auth_providers`
  array records which methods have been used).
- No pre-authorized allowlist — any Google account works during preview.

## Curl smoke tests

```
API=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d= -f2)

# Login as admin, save cookies
curl -c /tmp/c.txt -X POST "$API/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@aipillu.studio","password":"aipilluAdmin@2026"}'

# Verify session
curl -b /tmp/c.txt "$API/api/auth/me"

# List admin's projects
curl -b /tmp/c.txt "$API/api/projects"
```
