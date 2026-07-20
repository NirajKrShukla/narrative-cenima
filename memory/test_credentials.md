# AiPillu Studio — Test Credentials

Last updated: 2026-07-20 (license + OTP rewrite)

## Seeded Admin (auto-created on backend startup)

- **Email**: `admin@aipillu.studio`
- **Password**: `aipilluAdmin@2026`
- **Role**: `admin`
- **Auth provider**: `email` (JWT)

The admin bypasses **both** the per-project ownership check AND the
license-required check on write endpoints. Test conftest also grants the admin
a 365-day active license at session start.

## New license & OTP endpoints (2026-07-20 rewrite)

### Auth
| Method | Path | Purpose |
| ------ | ---- | ------- |
| POST | `/api/auth/register` | Email + password signup |
| POST | `/api/auth/login` | Email + password login |
| POST | `/api/auth/logout` | Clears all auth cookies |
| GET  | `/api/auth/me` | Returns the current user (401 if guest) |
| POST | `/api/auth/refresh` | Refresh the access_token cookie |
| POST | `/api/auth/session` | Emergent Google session exchange |

### OTP (email + phone, sandbox in preview)
| Method | Path | Body |
| ------ | ---- | ---- |
| POST | `/api/otp/send`   | `{channel: "email"\|"phone", identifier}` |
| POST | `/api/otp/verify` | `{channel, identifier, code}` |

In **sandbox mode** (`SANDBOX_MODE=true` or missing provider keys), `/otp/send`
returns the 6-digit code in the response body as `sandbox_code` so the UI can
auto-fill it. In production mode, codes are sent via Twilio Verify (SMS) and
Resend (email).

### Licenses (public plans + per-user actions)
| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET  | `/api/licenses/plans` | **Public** — 5 plans in INR |
| GET  | `/api/licenses/status` | Current user's license + verification state |
| POST | `/api/licenses/start-trial` | Activate the one-time 7-day trial (requires both OTPs verified) |
| POST | `/api/licenses/checkout` | Create a Razorpay order OR (sandbox) return a fake order |
| POST | `/api/licenses/checkout/verify` | Verify Razorpay signature + activate license |
| POST | `/api/licenses/checkout/sandbox-complete` | Sandbox-only — instantly grants the license |
| POST | `/api/webhooks/razorpay` | **Public** — signature-verified idempotent webhook |

### Plan tiers (INR)

| Plan | Days | Price | Notes |
| ---- | ---- | ----- | ----- |
| Free trial | 7 | ₹0 | One-time; requires email + phone verification |
| 30 days | 30 | ₹99 | Popular |
| 60 days | 60 | ₹170 | |
| 90 days | 90 | ₹260 | |
| 1 year | 365 | ₹950 | Max validity cap = 365 days from now |

## Gating summary (post 2026-07-20)

- **Public** (no login): `/`, `/pricing`, landing demos via `/api/storage/demo_*`, `/api/licenses/plans`, `/api/webhooks/razorpay`, `/api/auth/*`, `/api/health`.
- **Auth required** (any signed-in user): `/gallery`, `/verify`, GET on `/api/projects/*` (read-only for expired-license users), GET `/api/projects/{pid}/film` (download own films).
- **Auth + active license required**: any POST/PUT/PATCH/DELETE outside the license-management allow-list — creating projects, dubs, ingestion, analyze, batch, publish, etc.
- **Auth + ownership** on `/api/projects/{pid}/*` (admins bypass).

## Environment variables (in `/app/backend/.env`)

**Currently in SANDBOX mode** (`SANDBOX_MODE=true`). To go live, set these:

```
TWILIO_ACCOUNT_SID=ACxxxx
TWILIO_AUTH_TOKEN=xxxx
TWILIO_VERIFY_SERVICE_SID=VAxxxx

RESEND_API_KEY=re_xxxx
SENDER_EMAIL=noreply@yourdomain.com

RAZORPAY_KEY_ID=rzp_test_xxxx  (or rzp_live_xxxx)
RAZORPAY_KEY_SECRET=xxxx
RAZORPAY_WEBHOOK_SECRET=xxxx

SANDBOX_MODE=false
```

Restart the backend after changing `.env`: `sudo supervisorctl restart backend`.

Webhook URL to register in Razorpay:
`https://narrative-cinema-30.emergent.host/api/webhooks/razorpay` (production)
`https://narrative-cinema-30.preview.emergentagent.com/api/webhooks/razorpay` (preview)
Subscribe to: `payment.captured`, `payment.failed`.

## Sandbox curl smoke tests

```bash
API=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d= -f2)

# Register
curl -c /tmp/c.txt -X POST "$API/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"secret123","name":"Test"}'

# Verify email OTP (sandbox_code returned inline)
RESP=$(curl -s -b /tmp/c.txt -X POST "$API/api/otp/send" \
  -H "Content-Type: application/json" \
  -d '{"channel":"email","identifier":"you@example.com"}')
CODE=$(echo "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin)['sandbox_code'])")
curl -b /tmp/c.txt -X POST "$API/api/otp/verify" \
  -H "Content-Type: application/json" \
  -d "{\"channel\":\"email\",\"identifier\":\"you@example.com\",\"code\":\"$CODE\"}"

# Verify phone the same way with channel: "phone" and a +91… number

# Start trial
curl -b /tmp/c.txt -X POST "$API/api/licenses/start-trial"

# Sandbox purchase 30-day plan (no real charge)
curl -b /tmp/c.txt -X POST "$API/api/licenses/checkout/sandbox-complete" \
  -H "Content-Type: application/json" \
  -d '{"plan_id":"m1"}'
```
