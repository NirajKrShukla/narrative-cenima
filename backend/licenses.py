"""License / subscription management for AiPillu Studio.

Business model (2026-07 rewrite):
  * One-time free trial: **7 days**, one per verified email + phone.
  * Paid tiers (INR, one-off charge, extends existing license if active):
      - ₹99   for 30 days
      - ₹170  for 60 days
      - ₹260  for 90 days
      - ₹950  for 365 days   (also the max validity cap — 1 year)
  * While a license is active: unlimited film creation, download & share.
  * When it expires: **read-only** — existing films can still be viewed &
    downloaded, but no new films / dubs / gallery uploads.

Every license row records:
    user_id, plan_id, source ("trial"|"paid"), starts_at, expires_at,
    payment_id (Razorpay), amount_paise, status ("active"|"expired"|"refunded").
Only the row with the largest `expires_at` in the future is "current".
"""
from __future__ import annotations
import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field

import auth

logger = logging.getLogger("aipillu.licenses")

# ---- Pricing config -------------------------------------------------------
# amount is in paise (Razorpay convention) — 100 paise = ₹1.
PLANS: list[dict] = [
    {"id": "trial",   "label": "Free Trial",  "days": 7,   "amount_paise": 0,     "source": "trial"},
    {"id": "m1",      "label": "30 days",     "days": 30,  "amount_paise": 9900,  "source": "paid"},
    {"id": "m2",      "label": "60 days",     "days": 60,  "amount_paise": 17000, "source": "paid"},
    {"id": "m3",      "label": "90 days",     "days": 90,  "amount_paise": 26000, "source": "paid"},
    {"id": "y1",      "label": "1 year",      "days": 365, "amount_paise": 95000, "source": "paid"},
]
PLANS_BY_ID = {p["id"]: p for p in PLANS}
MAX_LICENSE_DAYS = 365  # hard cap — see spec


# ---- Collections binding (injected from server.py) ------------------------
_licenses_col = None
_users_col = None


def bind_collections(licenses_col, users_col) -> None:
    global _licenses_col, _users_col
    _licenses_col = licenses_col
    _users_col = users_col


async def ensure_indexes(licenses_col) -> None:
    await licenses_col.create_index("user_id")
    await licenses_col.create_index([("user_id", 1), ("expires_at", -1)])
    # Unique on payment_id but only for documents where it actually exists —
    # partialFilterExpression avoids Mongo's null-uniqueness caveat.
    await licenses_col.create_index(
        "payment_id",
        unique=True,
        partialFilterExpression={"payment_id": {"$type": "string"}},
        name="payment_id_unique_string",
    )


# ---- Query helpers --------------------------------------------------------
async def current_license(user_id: str) -> Optional[dict]:
    """Return the license with the furthest-future expiry (or None)."""
    if _licenses_col is None:
        return None
    doc = await _licenses_col.find_one(
        {"user_id": user_id, "status": "active"},
        sort=[("expires_at", -1)],
        projection={"_id": 0},
    )
    return doc


async def has_active_license(user_id: str) -> bool:
    lic = await current_license(user_id)
    if not lic:
        return False
    exp = lic.get("expires_at")
    if isinstance(exp, str):
        try:
            exp = datetime.fromisoformat(exp)
        except Exception:
            return False
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return exp > datetime.now(timezone.utc)


async def has_used_trial(user_id: str) -> bool:
    if _licenses_col is None:
        return False
    return bool(await _licenses_col.find_one(
        {"user_id": user_id, "source": "trial"}, {"_id": 1}
    ))


async def _insert_license(
    user_id: str, plan_id: str, source: str,
    payment_id: Optional[str] = None, amount_paise: int = 0,
    extend: bool = True,
) -> dict:
    """Insert a license row. If `extend=True` and a future license already exists,
    start this one at that license's `expires_at` instead of now (so users don't
    lose days by renewing early). Caps total future validity at 365 days out."""
    plan = PLANS_BY_ID.get(plan_id)
    if not plan:
        raise ValueError(f"Unknown plan: {plan_id}")

    now = datetime.now(timezone.utc)
    start_at = now
    if extend:
        existing = await current_license(user_id)
        if existing:
            exp = existing.get("expires_at")
            if isinstance(exp, datetime):
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp > now:
                    start_at = exp

    expires_at = start_at + timedelta(days=plan["days"])
    # Cap at 1 year from `now` — spec: max license period 365 days.
    max_expiry = now + timedelta(days=MAX_LICENSE_DAYS)
    if expires_at > max_expiry:
        expires_at = max_expiry

    doc = {
        "id": f"lic_{uuid.uuid4().hex[:12]}",
        "user_id": user_id,
        "plan_id": plan_id,
        "plan_label": plan["label"],
        "source": source,               # "trial" | "paid"
        "starts_at": start_at,
        "expires_at": expires_at,
        "amount_paise": amount_paise,
        "status": "active",
        "created_at": now,
    }
    if payment_id:
        doc["payment_id"] = payment_id
    await _licenses_col.insert_one(dict(doc))
    return doc


def _lic_public(doc: Optional[dict]) -> Optional[dict]:
    if not doc:
        return None
    def iso(v):
        return v.isoformat() if isinstance(v, datetime) else v
    now = datetime.now(timezone.utc)
    exp = doc.get("expires_at")
    if isinstance(exp, str):
        try:
            exp = datetime.fromisoformat(exp)
        except Exception:
            exp = None
    days_remaining = 0
    active = False
    if isinstance(exp, datetime):
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        delta = exp - now
        if delta.total_seconds() > 0:
            active = True
            days_remaining = int(delta.total_seconds() // 86400) + 1
    return {
        "id": doc.get("id"),
        "plan_id": doc.get("plan_id"),
        "plan_label": doc.get("plan_label"),
        "source": doc.get("source"),
        "starts_at": iso(doc.get("starts_at")),
        "expires_at": iso(doc.get("expires_at")),
        "amount_paise": doc.get("amount_paise", 0),
        "amount_inr": (doc.get("amount_paise", 0) or 0) / 100,
        "payment_id": doc.get("payment_id"),
        "status": doc.get("status"),
        "active": active,
        "days_remaining": days_remaining,
    }


# ---- Router ---------------------------------------------------------------
router = APIRouter(prefix="/api/licenses", tags=["licenses"])


def plans_public() -> list[dict]:
    return [
        {
            "id": p["id"],
            "label": p["label"],
            "days": p["days"],
            "amount_paise": p["amount_paise"],
            "amount_inr": p["amount_paise"] / 100,
            "source": p["source"],
        }
        for p in PLANS
    ]


@router.get("/plans")
async def get_plans():
    return {"plans": plans_public(), "currency": "INR"}


@router.get("/status")
async def status(user: dict = Depends(auth.get_current_user)):
    """Full license status for the signed-in user."""
    lic = await current_license(user["user_id"])
    trial_used = await has_used_trial(user["user_id"])
    is_admin = user.get("role") == "admin"
    verifications = {
        "email_verified": bool(user.get("email_verified")) or is_admin,
        "phone_verified": bool(user.get("phone_verified")) or is_admin,
    }
    can_start_trial = (
        not trial_used
        and not is_admin
        and verifications["email_verified"]
        and verifications["phone_verified"]
    )
    # Admins can always create films regardless of license state
    can_create_films = is_admin or await has_active_license(user["user_id"])
    return {
        "license": _lic_public(lic),
        "trial_used": trial_used,
        "can_start_trial": can_start_trial,
        "verifications": verifications,
        "can_create_films": can_create_films,
        "is_admin": is_admin,
        "plans": plans_public(),
    }


class StartTrialBody(BaseModel):
    pass  # kept for future flags


@router.post("/start-trial")
async def start_trial(user: dict = Depends(auth.get_current_user)):
    """Activate the one-time 7-day free trial. Requires **both** email & phone verified."""
    if not user.get("email_verified") or not user.get("phone_verified"):
        raise HTTPException(400, "Please verify your email AND mobile number before starting the free trial.")
    if await has_used_trial(user["user_id"]):
        raise HTTPException(409, "You've already used your one-time free trial. Please choose a paid plan.")
    if await has_active_license(user["user_id"]):
        raise HTTPException(409, "You already have an active license.")
    doc = await _insert_license(
        user_id=user["user_id"], plan_id="trial", source="trial", extend=False,
    )
    return {"ok": True, "license": _lic_public(doc)}


# ---- Paid checkout (Razorpay) --------------------------------------------
class CheckoutBody(BaseModel):
    plan_id: str = Field(pattern="^(m1|m2|m3|y1)$")


def _razorpay_client():
    import razorpay
    kid = os.environ.get("RAZORPAY_KEY_ID")
    sec = os.environ.get("RAZORPAY_KEY_SECRET")
    if not kid or not sec:
        return None
    return razorpay.Client(auth=(kid, sec))


@router.post("/checkout")
async def create_checkout(body: CheckoutBody, user: dict = Depends(auth.get_current_user)):
    """Create a Razorpay order for a paid plan.
    In SANDBOX_MODE (no keys), we return a fake order and the frontend can call
    /licenses/checkout/sandbox-complete to instantly unlock — useful for testing.
    """
    plan = PLANS_BY_ID.get(body.plan_id)
    if not plan or plan["source"] != "paid":
        raise HTTPException(400, "Invalid plan")

    client = _razorpay_client()
    sandbox = client is None or os.environ.get("SANDBOX_MODE", "").lower() == "true"

    if sandbox:
        return {
            "sandbox": True,
            "order_id": f"order_sandbox_{uuid.uuid4().hex[:10]}",
            "amount_paise": plan["amount_paise"],
            "amount_inr": plan["amount_paise"] / 100,
            "currency": "INR",
            "plan": {
                "id": plan["id"], "label": plan["label"], "days": plan["days"],
            },
            "key_id": None,
            "message": "Sandbox mode — call /api/licenses/checkout/sandbox-complete to unlock without paying.",
        }

    # Live Razorpay order creation
    try:
        order = client.order.create({
            "amount": plan["amount_paise"],
            "currency": "INR",
            "receipt": f"aipl_{user['user_id'][:16]}_{plan['id']}",
            "notes": {
                "user_id": user["user_id"],
                "email": user["email"],
                "plan_id": plan["id"],
            },
        })
    except Exception as e:
        logger.error(f"Razorpay order.create failed: {e}")
        raise HTTPException(502, f"Payment gateway error: {e}")

    return {
        "sandbox": False,
        "order_id": order["id"],
        "amount_paise": order["amount"],
        "amount_inr": order["amount"] / 100,
        "currency": order["currency"],
        "key_id": os.environ.get("RAZORPAY_KEY_ID"),
        "plan": {"id": plan["id"], "label": plan["label"], "days": plan["days"]},
    }


class SandboxCompleteBody(BaseModel):
    plan_id: str


@router.post("/checkout/sandbox-complete")
async def sandbox_complete(body: SandboxCompleteBody, user: dict = Depends(auth.get_current_user)):
    """SANDBOX ONLY: instantly grant the license without any real payment.
    Guarded so it only works while SANDBOX_MODE=true."""
    if os.environ.get("SANDBOX_MODE", "").lower() != "true":
        raise HTTPException(403, "Sandbox complete is disabled in live mode")
    plan = PLANS_BY_ID.get(body.plan_id)
    if not plan or plan["source"] != "paid":
        raise HTTPException(400, "Invalid plan")
    doc = await _insert_license(
        user_id=user["user_id"],
        plan_id=body.plan_id,
        source="paid",
        payment_id=f"pay_sandbox_{uuid.uuid4().hex[:10]}",
        amount_paise=plan["amount_paise"],
        extend=True,
    )
    return {"ok": True, "sandbox": True, "license": _lic_public(doc)}


class VerifyPaymentBody(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    plan_id: str


@router.post("/checkout/verify")
async def verify_payment(body: VerifyPaymentBody, user: dict = Depends(auth.get_current_user)):
    """Verify a Razorpay checkout callback and activate the license."""
    plan = PLANS_BY_ID.get(body.plan_id)
    if not plan or plan["source"] != "paid":
        raise HTTPException(400, "Invalid plan")

    client = _razorpay_client()
    if client is None:
        raise HTTPException(503, "Razorpay not configured — set RAZORPAY_KEY_ID/SECRET in .env")

    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": body.razorpay_order_id,
            "razorpay_payment_id": body.razorpay_payment_id,
            "razorpay_signature": body.razorpay_signature,
        })
    except Exception as e:
        logger.error(f"Signature verification failed: {e}")
        raise HTTPException(400, "Payment signature verification failed")

    # Idempotency — if we already recorded this payment, return existing
    if _licenses_col is not None:
        prev = await _licenses_col.find_one(
            {"payment_id": body.razorpay_payment_id}, {"_id": 0}
        )
        if prev:
            return {"ok": True, "license": _lic_public(prev), "already_recorded": True}

    doc = await _insert_license(
        user_id=user["user_id"],
        plan_id=body.plan_id,
        source="paid",
        payment_id=body.razorpay_payment_id,
        amount_paise=plan["amount_paise"],
        extend=True,
    )
    return {"ok": True, "license": _lic_public(doc)}


# ---- Webhook --------------------------------------------------------------
async def handle_razorpay_webhook(request: Request) -> dict:
    """Called from server.py Stripe/webhook block."""
    payload_bytes = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(503, "Razorpay webhook secret not configured")
    client = _razorpay_client()
    if client is None:
        raise HTTPException(503, "Razorpay not configured")
    try:
        client.utility.verify_webhook_signature(
            payload_bytes.decode("utf-8"), signature, secret,
        )
    except Exception as e:
        logger.error(f"Razorpay webhook signature failed: {e}")
        raise HTTPException(400, "Invalid webhook signature")

    import json
    body = json.loads(payload_bytes.decode("utf-8"))
    event = body.get("event")
    payment = (body.get("payload", {}) or {}).get("payment", {}).get("entity", {})

    if event == "payment.captured":
        notes = payment.get("notes") or {}
        user_id = notes.get("user_id")
        plan_id = notes.get("plan_id")
        pay_id = payment.get("id")
        plan = PLANS_BY_ID.get(plan_id)
        if user_id and plan and plan["source"] == "paid" and pay_id:
            existing = await _licenses_col.find_one({"payment_id": pay_id}, {"_id": 1})
            if not existing:
                await _insert_license(
                    user_id=user_id, plan_id=plan_id, source="paid",
                    payment_id=pay_id, amount_paise=payment.get("amount", 0),
                    extend=True,
                )
                logger.info(f"Webhook activated license for {user_id} via {plan_id}")
    return {"received": True}


# ---- Middleware helper — used by server.py -------------------------------
async def require_active_license(user: dict) -> None:
    if user.get("role") == "admin":
        return
    if not await has_active_license(user["user_id"]):
        raise HTTPException(
            402,
            "Your license has expired or you don't have one yet. "
            "Please start your 7-day free trial or purchase a plan to continue.",
        )
