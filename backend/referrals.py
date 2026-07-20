"""Referral credits — 'invite a friend, both get +7 days'.

Model:
  * Every user gets a random 8-char `referral_code` on signup (auto-generated).
  * New signup can pass `referred_by=<code>` — we record the pending relationship.
  * When the referee's first OTP is verified (real human), BOTH sides get
    +7 days added to their current license (or a fresh 7-day 'referral' license
    if either doesn't have one yet).
  * Each referee can only trigger ONE reward (idempotent), and no self-referrals.
  * Bounded by the 365-day max validity cap already in licenses.py.
"""
from __future__ import annotations
import uuid
import secrets
import string
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

import auth
import licenses as licenses_mod

logger = logging.getLogger("aipillu.referrals")

REFERRAL_BONUS_DAYS = 7
CODE_ALPHABET = string.ascii_uppercase + string.digits
CODE_LENGTH = 8

_users_col = None
_licenses_col = None
_referrals_col = None


def bind_collections(users_col, licenses_col, referrals_col) -> None:
    global _users_col, _licenses_col, _referrals_col
    _users_col = users_col
    _licenses_col = licenses_col
    _referrals_col = referrals_col


async def ensure_indexes(users_col, referrals_col) -> None:
    await users_col.create_index("referral_code", unique=True, sparse=True)
    await referrals_col.create_index("referee_user_id", unique=True)
    await referrals_col.create_index("referrer_user_id")


def _generate_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


async def ensure_user_code(user_id: str) -> str:
    """Return this user's referral code, generating one if missing."""
    doc = await _users_col.find_one({"user_id": user_id}, {"referral_code": 1})
    code = (doc or {}).get("referral_code")
    if code:
        return code
    # Retry-on-collision loop (rare — 36^8 space)
    for _ in range(5):
        candidate = _generate_code()
        try:
            await _users_col.update_one(
                {"user_id": user_id, "referral_code": {"$exists": False}},
                {"$set": {"referral_code": candidate}},
            )
            check = await _users_col.find_one({"user_id": user_id}, {"referral_code": 1})
            if check and check.get("referral_code"):
                return check["referral_code"]
        except Exception as e:
            logger.warning(f"referral code gen retry: {e}")
    raise HTTPException(500, "Could not generate referral code")


async def record_pending(referrer_code: str, referee_user_id: str) -> None:
    """Called at register-time when the user pastes a referral code."""
    if not referrer_code:
        return
    referrer = await _users_col.find_one({"referral_code": referrer_code.upper()}, {"user_id": 1, "email": 1})
    if not referrer:
        return  # Silently ignore invalid codes
    if referrer["user_id"] == referee_user_id:
        return  # No self-referrals
    try:
        await _referrals_col.insert_one({
            "id": f"ref_{uuid.uuid4().hex[:12]}",
            "referrer_user_id": referrer["user_id"],
            "referee_user_id": referee_user_id,
            "code_used": referrer_code.upper(),
            "status": "pending",
            "created_at": datetime.now(timezone.utc),
        })
    except Exception:
        pass  # unique key on referee — already recorded


async def maybe_award(referee_user_id: str) -> Optional[dict]:
    """Called after the referee's FIRST OTP verification succeeds.
    Awards +7 days to BOTH parties, idempotently. Returns the referral doc or None."""
    if _referrals_col is None:
        return None
    ref = await _referrals_col.find_one({"referee_user_id": referee_user_id, "status": "pending"})
    if not ref:
        return None

    # Award both users +7 days
    for uid in (ref["referrer_user_id"], ref["referee_user_id"]):
        try:
            await _insert_bonus_days(uid, REFERRAL_BONUS_DAYS, note=f"referral bonus ({ref['id']})")
        except Exception as e:
            logger.error(f"referral award to {uid} failed: {e}")

    await _referrals_col.update_one(
        {"id": ref["id"]},
        {"$set": {"status": "awarded", "awarded_at": datetime.now(timezone.utc)}},
    )
    ref["status"] = "awarded"
    return ref


async def _insert_bonus_days(user_id: str, days: int, note: str = "") -> None:
    """Extend the user's current license by `days`, or create a fresh referral
    license if they have none. Respects the 365-day validity cap."""
    now = datetime.now(timezone.utc)
    lic = await licenses_mod.current_license(user_id)
    start_at = now
    if lic:
        exp = lic.get("expires_at")
        if isinstance(exp, datetime):
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp > now:
                start_at = exp
    expires_at = start_at + timedelta(days=days)
    max_expiry = now + timedelta(days=licenses_mod.MAX_LICENSE_DAYS)
    if expires_at > max_expiry:
        expires_at = max_expiry

    doc = {
        "id": f"lic_{uuid.uuid4().hex[:12]}",
        "user_id": user_id,
        "plan_id": "referral",
        "plan_label": f"Referral bonus (+{days}d)",
        "source": "referral",
        "starts_at": start_at,
        "expires_at": expires_at,
        "amount_paise": 0,
        "status": "active",
        "note": note,
        "created_at": now,
    }
    await _licenses_col.insert_one(dict(doc))


# ---------- Router ----------
router = APIRouter(prefix="/api/referrals", tags=["referrals"])


@router.get("/me")
async def my_referral(user: dict = Depends(auth.get_current_user)):
    code = await ensure_user_code(user["user_id"])
    referred = await _referrals_col.count_documents({
        "referrer_user_id": user["user_id"], "status": "awarded",
    })
    pending = await _referrals_col.count_documents({
        "referrer_user_id": user["user_id"], "status": "pending",
    })
    return {
        "code": code,
        "referred_count": referred,
        "pending_count": pending,
        "bonus_days_per_referral": REFERRAL_BONUS_DAYS,
    }


class ValidateBody(BaseModel):
    code: str


@router.post("/validate")
async def validate_code(body: ValidateBody):
    """Public — used on the register form to preview which user's code it is."""
    if _users_col is None:
        raise HTTPException(503, "Not ready")
    doc = await _users_col.find_one(
        {"referral_code": body.code.strip().upper()},
        {"name": 1, "email": 1},
    )
    if not doc:
        raise HTTPException(404, "Invalid referral code")
    return {
        "valid": True,
        "referrer_hint": (doc.get("name") or (doc.get("email", "").split("@")[0])) + " invited you",
        "bonus_days": REFERRAL_BONUS_DAYS,
    }
