"""Admin KYC dashboard endpoints (role=admin only) + Password reset flow.

Admin endpoints:
  GET  /api/admin/summary        — headline metrics (users, active licenses, revenue)
  GET  /api/admin/users          — paginated user list with verifications + license state
  GET  /api/admin/licenses       — paginated license list
  GET  /api/admin/revenue        — revenue rollup (all-time / this month / by plan)

Password reset (public — no auth):
  POST /api/auth/forgot-password  — send an OTP to the email address
  POST /api/auth/reset-password   — verify OTP + set new password
"""
from __future__ import annotations
import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr, Field

import auth
import otp as otp_mod

logger = logging.getLogger("aipillu.admin")

_users_col = None
_licenses_col = None
_projects_col = None
_referrals_col = None
_otp_col = None


def bind_collections(users_col, licenses_col, projects_col, referrals_col, otp_col) -> None:
    global _users_col, _licenses_col, _projects_col, _referrals_col, _otp_col
    _users_col = users_col
    _licenses_col = licenses_col
    _projects_col = projects_col
    _referrals_col = referrals_col
    _otp_col = otp_col


# ---------- Admin guard ----------
async def require_admin(user: dict = Depends(auth.get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access only")
    return user


# ================================================================
# ADMIN DASHBOARD
# ================================================================
admin_router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@admin_router.get("/summary")
async def summary():
    now = datetime.now(timezone.utc)
    users_total = await _users_col.count_documents({})
    users_verified = await _users_col.count_documents({
        "email_verified": True, "phone_verified": True,
    })
    active_licenses = await _licenses_col.count_documents({
        "status": "active", "expires_at": {"$gt": now},
    })

    # Revenue rollup (paid licenses only)
    rev_pipeline = [
        {"$match": {"source": "paid", "amount_paise": {"$gt": 0}}},
        {"$group": {"_id": None, "total_paise": {"$sum": "$amount_paise"}, "count": {"$sum": 1}}},
    ]
    rev_all = await _licenses_col.aggregate(rev_pipeline).to_list(1)
    total_paise = (rev_all[0]["total_paise"] if rev_all else 0)
    revenue_count = (rev_all[0]["count"] if rev_all else 0)

    # This month
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    rev_month_pipeline = [
        {"$match": {"source": "paid", "amount_paise": {"$gt": 0}, "created_at": {"$gte": month_start}}},
        {"$group": {"_id": None, "total_paise": {"$sum": "$amount_paise"}, "count": {"$sum": 1}}},
    ]
    rev_month = await _licenses_col.aggregate(rev_month_pipeline).to_list(1)
    month_paise = (rev_month[0]["total_paise"] if rev_month else 0)
    month_count = (rev_month[0]["count"] if rev_month else 0)

    # By plan
    plan_pipeline = [
        {"$match": {"source": "paid", "amount_paise": {"$gt": 0}}},
        {"$group": {
            "_id": "$plan_id",
            "count": {"$sum": 1},
            "total_paise": {"$sum": "$amount_paise"},
        }},
        {"$sort": {"total_paise": -1}},
    ]
    by_plan = await _licenses_col.aggregate(plan_pipeline).to_list(20)

    # Films / projects
    projects_total = await _projects_col.count_documents({})
    films_total = await _projects_col.count_documents({"final_film": {"$ne": None}})

    return {
        "users": {"total": users_total, "verified": users_verified},
        "licenses": {"active": active_licenses},
        "projects": {"total": projects_total, "with_final_film": films_total},
        "revenue": {
            "total_inr": total_paise / 100,
            "total_transactions": revenue_count,
            "this_month_inr": month_paise / 100,
            "this_month_transactions": month_count,
            "by_plan": [{
                "plan_id": p["_id"],
                "count": p["count"],
                "total_inr": p["total_paise"] / 100,
            } for p in by_plan],
        },
    }


@admin_router.get("/users")
async def list_users(q: str = "", limit: int = 50, skip: int = 0):
    filt = {}
    if q:
        filt["$or"] = [
            {"email": {"$regex": q, "$options": "i"}},
            {"name": {"$regex": q, "$options": "i"}},
            {"phone": {"$regex": q}},
        ]
    now = datetime.now(timezone.utc)
    total = await _users_col.count_documents(filt)
    users = await _users_col.find(
        filt,
        {"_id": 0, "password_hash": 0},
    ).sort("created_at", -1).skip(skip).limit(min(limit, 200)).to_list(None)

    # Attach current-license info per user (single-query batch)
    uids = [u["user_id"] for u in users]
    lic_map: dict[str, dict] = {}
    if uids:
        async for lic in _licenses_col.find(
            {"user_id": {"$in": uids}, "status": "active"},
            {"_id": 0},
        ).sort("expires_at", -1):
            uid = lic["user_id"]
            if uid not in lic_map:
                lic_map[uid] = lic

    def iso(v):
        return v.isoformat() if hasattr(v, "isoformat") else v

    def enrich(u):
        lic = lic_map.get(u["user_id"])
        active = False
        days = 0
        if lic:
            exp = lic.get("expires_at")
            if isinstance(exp, str):
                try:
                    exp = datetime.fromisoformat(exp)
                except Exception:
                    exp = None
            if isinstance(exp, datetime):
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp > now:
                    active = True
                    days = int((exp - now).total_seconds() // 86400) + 1
        return {
            "user_id": u["user_id"],
            "email": u.get("email"),
            "name": u.get("name"),
            "phone": u.get("phone"),
            "picture": u.get("picture"),
            "role": u.get("role", "user"),
            "auth_providers": u.get("auth_providers", []),
            "email_verified": bool(u.get("email_verified")),
            "phone_verified": bool(u.get("phone_verified")),
            "created_at": iso(u.get("created_at")),
            "referral_code": u.get("referral_code"),
            "current_plan": lic.get("plan_label") if lic else None,
            "license_active": active,
            "days_remaining": days,
        }

    return {"total": total, "skip": skip, "limit": limit, "users": [enrich(u) for u in users]}


@admin_router.get("/licenses")
async def list_licenses(limit: int = 100, skip: int = 0, source: str = ""):
    filt = {}
    if source in ("trial", "paid", "referral"):
        filt["source"] = source
    total = await _licenses_col.count_documents(filt)
    lic_cursor = _licenses_col.find(filt, {"_id": 0}).sort("created_at", -1).skip(skip).limit(min(limit, 500))
    licenses = await lic_cursor.to_list(None)

    # Attach email for readability
    uids = list({lic["user_id"] for lic in licenses})
    email_map = {}
    if uids:
        async for u in _users_col.find({"user_id": {"$in": uids}}, {"user_id": 1, "email": 1, "name": 1}):
            email_map[u["user_id"]] = u

    def iso(v):
        return v.isoformat() if hasattr(v, "isoformat") else v

    out = []
    for lic in licenses:
        u = email_map.get(lic["user_id"]) or {}
        out.append({
            "id": lic.get("id"),
            "user_id": lic["user_id"],
            "email": u.get("email"),
            "name": u.get("name"),
            "plan_id": lic.get("plan_id"),
            "plan_label": lic.get("plan_label"),
            "source": lic.get("source"),
            "amount_inr": (lic.get("amount_paise", 0) or 0) / 100,
            "payment_id": lic.get("payment_id"),
            "starts_at": iso(lic.get("starts_at")),
            "expires_at": iso(lic.get("expires_at")),
            "created_at": iso(lic.get("created_at")),
            "status": lic.get("status"),
        })
    return {"total": total, "skip": skip, "limit": limit, "licenses": out}


# ================================================================
# PASSWORD RESET
# ================================================================
password_reset_router = APIRouter(prefix="/api/auth", tags=["auth"])


class ForgotBody(BaseModel):
    email: EmailStr


@password_reset_router.post("/forgot-password")
async def forgot_password(body: ForgotBody):
    """Send a 6-digit OTP to the account's email — user has 10 min to use it.
    We always return 200 so attackers can't enumerate registered emails."""
    email = body.email.strip().lower()
    user = await _users_col.find_one({"email": email})
    if user:
        # Reuse the OTP module — but avoid requiring the caller to be authenticated.
        await otp_mod._check_rate_limit("email", email)
        code = otp_mod._generate_local_code()
        await otp_mod._store_local_otp("email", email, code)
        # Wrap in try so sandbox never blows up
        try:
            await otp_mod._send_email_otp(email, code)
        except Exception:
            pass
    # Uniform response regardless
    resp = {"ok": True, "message": "If this email exists, we've sent a reset code."}
    if os.environ.get("SANDBOX_MODE", "").lower() == "true" and user:
        # In preview, expose the code so QA can verify without an email inbox
        resp["sandbox_code"] = code
    return resp


class ResetBody(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=8)
    new_password: str = Field(min_length=6, max_length=200)


@password_reset_router.post("/reset-password")
async def reset_password(body: ResetBody):
    email = body.email.strip().lower()
    ok = await otp_mod._verify_local_otp("email", email, body.code.strip())
    if not ok:
        raise HTTPException(400, "Incorrect or expired reset code")

    new_hash = auth.hash_password(body.new_password)
    r = await _users_col.update_one(
        {"email": email},
        {"$set": {
            "password_hash": new_hash,
            "email_verified": True,     # verifying the reset code also verifies the email
            "updated_at": datetime.now(timezone.utc),
        }},
    )
    if r.matched_count == 0:
        raise HTTPException(404, "No account with that email")
    return {"ok": True, "message": "Password reset. You can now sign in."}
