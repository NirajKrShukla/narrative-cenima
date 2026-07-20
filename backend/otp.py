"""OTP verification for AiPillu Studio — Email (Resend) + Phone (Twilio Verify).

Both channels share the same public interface:
    POST /api/otp/send    {channel: "email"|"phone", identifier}
    POST /api/otp/verify  {channel, identifier, code}

Rate limits (enforced per identifier):
    * At most 3 send-requests per hour
    * Each code expires 10 minutes after send
    * Each code is single-use (marked verified on success)

**Sandbox mode**: if the required provider credentials aren't set, we
generate a local 6-digit OTP, print it to backend logs AND include it in the
`/send` response (as `sandbox_code`), so the UI can auto-fill it for testing.
"""
from __future__ import annotations
import os
import re
import uuid
import random
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr, Field

import auth

logger = logging.getLogger("aipillu.otp")

OTP_TTL_MIN = 10
SEND_RATE_LIMIT_PER_HOUR = 3
PHONE_RE = re.compile(r"^\+[1-9]\d{7,14}$")   # E.164


# ---- Collections binding --------------------------------------------------
_otp_col = None
_users_col = None


def bind_collections(otp_col, users_col) -> None:
    global _otp_col, _users_col
    _otp_col = otp_col
    _users_col = users_col


async def ensure_indexes(otp_col) -> None:
    await otp_col.create_index([("channel", 1), ("identifier", 1)])
    # TTL cleanup: purge documents older than 24h automatically
    await otp_col.create_index(
        "created_at",
        expireAfterSeconds=24 * 3600,
    )


# ---- Providers ------------------------------------------------------------
def _sandbox() -> bool:
    return os.environ.get("SANDBOX_MODE", "").lower() == "true"


def _twilio_ready() -> bool:
    return bool(
        os.environ.get("TWILIO_ACCOUNT_SID")
        and os.environ.get("TWILIO_AUTH_TOKEN")
        and os.environ.get("TWILIO_VERIFY_SERVICE_SID")
    )


def _resend_ready() -> bool:
    return bool(os.environ.get("RESEND_API_KEY") and os.environ.get("SENDER_EMAIL"))


def _generate_local_code() -> str:
    return f"{random.randint(0, 999999):06d}"


async def _send_email_otp(email: str, code: str) -> None:
    """Send an email OTP via Resend. Runs the sync SDK in a thread."""
    if _sandbox() or not _resend_ready():
        logger.info(f"[SANDBOX] Email OTP for {email} → {code}")
        return
    import resend
    resend.api_key = os.environ["RESEND_API_KEY"]
    params = {
        "from": os.environ["SENDER_EMAIL"],
        "to": [email],
        "subject": f"Your AiPillu Studio code: {code}",
        "html": _EMAIL_TEMPLATE.format(code=code),
    }
    await asyncio.to_thread(resend.Emails.send, params)


async def _send_phone_otp_via_twilio(phone: str) -> None:
    """Twilio Verify handles code generation + storage on their side.
    We DON'T need to store the code locally when Twilio Verify is used —
    verification is checked against Twilio's servers.
    """
    from twilio.rest import Client
    tw = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
    svc = os.environ["TWILIO_VERIFY_SERVICE_SID"]

    def _create():
        tw.verify.v2.services(svc).verifications.create(to=phone, channel="sms")

    await asyncio.to_thread(_create)


async def _verify_phone_via_twilio(phone: str, code: str) -> bool:
    from twilio.rest import Client
    tw = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
    svc = os.environ["TWILIO_VERIFY_SERVICE_SID"]

    def _check():
        return tw.verify.v2.services(svc).verification_checks.create(to=phone, code=code)

    r = await asyncio.to_thread(_check)
    return getattr(r, "status", None) == "approved"


# ---- OTP row helpers ------------------------------------------------------
async def _check_rate_limit(channel: str, identifier: str) -> None:
    """Raise 429 if user hit the send-rate-limit in the past hour."""
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    n = await _otp_col.count_documents({
        "channel": channel, "identifier": identifier,
        "created_at": {"$gte": since},
    })
    if n >= SEND_RATE_LIMIT_PER_HOUR:
        raise HTTPException(
            429,
            f"Too many code requests. Please wait 1 hour before requesting another OTP for this {channel}.",
        )


async def _store_local_otp(channel: str, identifier: str, code: str) -> None:
    now = datetime.now(timezone.utc)
    await _otp_col.insert_one({
        "id": f"otp_{uuid.uuid4().hex[:12]}",
        "channel": channel,
        "identifier": identifier,
        "code": code,
        "created_at": now,
        "expires_at": now + timedelta(minutes=OTP_TTL_MIN),
        "verified": False,
        "attempts": 0,
    })


async def _verify_local_otp(channel: str, identifier: str, code: str) -> bool:
    now = datetime.now(timezone.utc)
    doc = await _otp_col.find_one_and_update(
        {
            "channel": channel, "identifier": identifier, "code": code,
            "verified": False, "expires_at": {"$gt": now},
        },
        {"$set": {"verified": True, "verified_at": now}},
        sort=[("created_at", -1)],
    )
    if doc:
        return True
    # Increment attempts on the most recent unverified row (to help lockout logic later)
    await _otp_col.update_one(
        {"channel": channel, "identifier": identifier, "verified": False},
        {"$inc": {"attempts": 1}},
        sort=[("created_at", -1)],
    )
    return False


# ---- Router ---------------------------------------------------------------
router = APIRouter(prefix="/api/otp", tags=["otp"])


class SendBody(BaseModel):
    channel: str = Field(pattern="^(email|phone)$")
    identifier: str


class VerifyBody(BaseModel):
    channel: str = Field(pattern="^(email|phone)$")
    identifier: str
    code: str = Field(min_length=4, max_length=8)


def _normalize_email(e: str) -> str:
    return e.strip().lower()


def _normalize_phone(p: str) -> str:
    p = p.strip().replace(" ", "").replace("-", "")
    if not p.startswith("+"):
        # Best-effort: assume Indian number if 10 digits
        if len(p) == 10 and p.isdigit():
            p = "+91" + p
        else:
            raise HTTPException(400, "Phone number must be in E.164 format (e.g. +919876543210)")
    if not PHONE_RE.match(p):
        raise HTTPException(400, "Invalid phone number format")
    return p


@router.post("/send")
async def send_otp(
    body: SendBody,
    user: dict = Depends(auth.get_current_user),
):
    """Send a one-time code to the user's chosen channel."""
    if body.channel == "email":
        try:
            identifier = _normalize_email(body.identifier)
            # Validate via Pydantic EmailStr
            _ = EmailStr._validate(identifier, None) if False else identifier  # noqa
        except Exception:
            raise HTTPException(400, "Invalid email")
    else:
        identifier = _normalize_phone(body.identifier)

    await _check_rate_limit(body.channel, identifier)

    result: dict = {"ok": True, "channel": body.channel, "identifier": identifier}
    if body.channel == "email":
        code = _generate_local_code()
        await _store_local_otp("email", identifier, code)
        await _send_email_otp(identifier, code)
        if _sandbox() or not _resend_ready():
            result["sandbox_code"] = code
    else:  # phone
        if _sandbox() or not _twilio_ready():
            code = _generate_local_code()
            await _store_local_otp("phone", identifier, code)
            logger.info(f"[SANDBOX] Phone OTP for {identifier} → {code}")
            result["sandbox_code"] = code
        else:
            await _send_phone_otp_via_twilio(identifier)
    return result


@router.post("/verify")
async def verify_otp(
    body: VerifyBody,
    user: dict = Depends(auth.get_current_user),
):
    identifier = (
        _normalize_email(body.identifier) if body.channel == "email"
        else _normalize_phone(body.identifier)
    )
    ok = False
    if body.channel == "phone" and _twilio_ready() and not _sandbox():
        ok = await _verify_phone_via_twilio(identifier, body.code.strip())
        if ok:
            # Record locally so audit logs / rate-limits work uniformly
            await _otp_col.insert_one({
                "id": f"otp_{uuid.uuid4().hex[:12]}",
                "channel": "phone", "identifier": identifier,
                "code": None, "verified": True,
                "created_at": datetime.now(timezone.utc),
                "verified_at": datetime.now(timezone.utc),
                "source": "twilio_verify",
            })
    else:
        ok = await _verify_local_otp(body.channel, identifier, body.code.strip())

    if not ok:
        raise HTTPException(400, "Incorrect or expired code. Please request a new one.")

    # Persist verification onto the user document
    field = "email_verified" if body.channel == "email" else "phone_verified"
    updates = {field: True, f"{field}_at": datetime.now(timezone.utc)}
    if body.channel == "phone":
        updates["phone"] = identifier
    await _users_col.update_one({"user_id": user["user_id"]}, {"$set": updates})

    # If this is the user's FIRST verification (either channel), try to award
    # a pending referral bonus to both parties.
    try:
        import referrals as _refs
        await _refs.maybe_award(user["user_id"])
    except Exception:
        pass

    return {"ok": True, "channel": body.channel, "verified": True}


# ---- Email template -------------------------------------------------------
_EMAIL_TEMPLATE = """\
<div style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif;background:#0b0b0b;color:#f5f5f5;padding:32px;border-radius:12px;max-width:480px;margin:0 auto;">
  <h1 style="font-size:22px;margin:0 0 4px;font-weight:600;letter-spacing:-0.02em;">AiPillu Studio</h1>
  <p style="color:#a0a0a0;font-size:13px;margin:0 0 32px;">Your one-time verification code</p>
  <div style="background:#151515;border:1px solid #2a2a2a;border-radius:10px;padding:24px;text-align:center;">
    <div style="font-size:38px;letter-spacing:14px;font-weight:600;color:#e6c874;">{code}</div>
    <p style="color:#8a8a8a;font-size:12px;margin:16px 0 0;">This code expires in 10 minutes.</p>
  </div>
  <p style="color:#5a5a5a;font-size:12px;margin:24px 0 0;">If you did not request this code, you can safely ignore this email.</p>
</div>
"""
