"""Unified authentication for AiPillu Studio.

Supports TWO parallel flows on the same `users` collection:
  1. Email + Password (bcrypt + JWT access/refresh cookies)
  2. Emergent-managed Google Auth (exchange `session_id` → `session_token` cookie)

`get_current_user` accepts EITHER auth method:
  - `access_token` cookie / `Authorization: Bearer <jwt>`   → JWT flow
  - `session_token` cookie / `Authorization: Bearer <session>` → Emergent flow

Every user is keyed by lowercase **email**, so the "1 free ≤20 MB unlock per user"
rule works uniformly whether the user signed in with Google or email/password.
"""
from __future__ import annotations
import os
import uuid
import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import bcrypt
import jwt as pyjwt
import httpx
from fastapi import APIRouter, HTTPException, Request, Response, Depends
from pydantic import BaseModel, EmailStr, Field

logger = logging.getLogger("aipillu.auth")

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MIN = 60 * 24 * 7        # 7 days (studio sessions can be long)
REFRESH_TOKEN_DAYS = 30
EMERGENT_SESSION_DAYS = 7
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------- Password hashing ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ---------- JWT ----------
def _jwt_secret() -> str:
    s = os.environ.get("JWT_SECRET")
    if not s:
        raise RuntimeError("JWT_SECRET is not configured")
    return s


def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id, "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_MIN),
        "type": "access",
    }
    return pyjwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DAYS),
        "type": "refresh",
    }
    return pyjwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


def _decode_jwt(token: str) -> Optional[dict]:
    try:
        return pyjwt.decode(token, _jwt_secret(), algorithms=[JWT_ALGORITHM])
    except Exception:
        return None


# ---------- Cookie helpers ----------
def _set_auth_cookies(resp: Response, access_token: str, refresh_token: str) -> None:
    resp.set_cookie(
        "access_token", access_token, httponly=True, secure=True, samesite="none",
        max_age=ACCESS_TOKEN_MIN * 60, path="/",
    )
    resp.set_cookie(
        "refresh_token", refresh_token, httponly=True, secure=True, samesite="none",
        max_age=REFRESH_TOKEN_DAYS * 86400, path="/",
    )


def _set_session_cookie(resp: Response, session_token: str) -> None:
    resp.set_cookie(
        "session_token", session_token, httponly=True, secure=True, samesite="none",
        max_age=EMERGENT_SESSION_DAYS * 86400, path="/",
    )


def _clear_all_auth_cookies(resp: Response) -> None:
    for k in ("access_token", "refresh_token", "session_token"):
        resp.delete_cookie(k, path="/", secure=True, samesite="none", httponly=True)


# ---------- Models ----------
class RegisterBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=200)
    name: Optional[str] = None
    referred_by: Optional[str] = None


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class SessionExchangeBody(BaseModel):
    session_id: str


class UserOut(BaseModel):
    user_id: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    role: str = "user"
    auth_providers: list[str] = Field(default_factory=list)


# ---------- Emergent session lookup ----------
EMERGENT_SESSION_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"


async def _emergent_lookup_session(session_id: str) -> dict:
    """Exchange a one-time session_id for the persistent user + session_token."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(
            EMERGENT_SESSION_URL, headers={"X-Session-ID": session_id},
        )
    if r.status_code != 200:
        raise HTTPException(401, f"Emergent session invalid: {r.status_code}")
    data = r.json()
    if not data.get("email"):
        raise HTTPException(401, "Emergent session missing email")
    return data


# ---------- get_current_user dependency ----------
# Injected by server.py at startup so this module has no direct DB import loop.
_users_col = None
_sessions_col = None


def bind_collections(users_col, sessions_col) -> None:
    global _users_col, _sessions_col
    _users_col = users_col
    _sessions_col = sessions_col


async def _user_by_id(uid: str) -> Optional[dict]:
    if _users_col is None:
        return None
    return await _users_col.find_one({"user_id": uid}, {"_id": 0, "password_hash": 0})


async def _user_by_email(email: str) -> Optional[dict]:
    if _users_col is None:
        return None
    return await _users_col.find_one({"email": email.lower()}, {"_id": 0})


async def get_current_user(request: Request) -> dict:
    """Authenticate via JWT cookie/header OR Emergent session_token cookie/header.
    Returns the user document (without password_hash). Raises 401 if not signed in."""
    # 1. Try JWT (access_token cookie or Bearer header)
    token = request.cookies.get("access_token")
    if not token:
        h = request.headers.get("Authorization", "")
        if h.startswith("Bearer "):
            token = h[7:]
    if token:
        payload = _decode_jwt(token)
        if payload and payload.get("type") == "access":
            user = await _user_by_id(payload["sub"])
            if user:
                return user

    # 2. Try Emergent session_token (cookie preferred, then header)
    st = request.cookies.get("session_token")
    if not st:
        h = request.headers.get("Authorization", "")
        if h.startswith("Bearer "):
            st = h[7:]
    if st and _sessions_col is not None:
        sess = await _sessions_col.find_one({"session_token": st}, {"_id": 0})
        if sess:
            exp = sess.get("expires_at")
            if isinstance(exp, str):
                try:
                    exp = datetime.fromisoformat(exp)
                except Exception:
                    exp = None
            if exp is not None:
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp >= datetime.now(timezone.utc):
                    user = await _user_by_id(sess["user_id"])
                    if user:
                        return user

    raise HTTPException(status_code=401, detail="Not authenticated")


async def optional_current_user(request: Request) -> Optional[dict]:
    """Same as get_current_user but returns None instead of 401 — for endpoints
    that behave differently for guests vs signed-in users."""
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


# ---------- Router ----------
router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_public(doc: dict) -> dict:
    return {
        "user_id": doc.get("user_id"),
        "email": doc.get("email"),
        "name": doc.get("name"),
        "picture": doc.get("picture"),
        "role": doc.get("role") or "user",
        "auth_providers": doc.get("auth_providers") or [],
        "email_verified": bool(doc.get("email_verified")),
        "phone_verified": bool(doc.get("phone_verified")),
        "phone": doc.get("phone"),
    }


async def _upsert_user_from_google(profile: dict) -> dict:
    """Look up user by email; create if missing; merge Google profile fields."""
    email = profile["email"].lower()
    existing = await _users_col.find_one({"email": email})
    now = datetime.now(timezone.utc)
    if existing:
        providers = set(existing.get("auth_providers") or [])
        providers.add("google")
        updates = {
            "auth_providers": list(providers),
            "name": existing.get("name") or profile.get("name"),
            "picture": profile.get("picture") or existing.get("picture"),
            "email_verified": True,   # Google verified the email for us
            "updated_at": now,
        }
        await _users_col.update_one({"email": email}, {"$set": updates})
        existing.update(updates)
        return existing

    doc = {
        "user_id": f"user_{uuid.uuid4().hex[:12]}",
        "email": email,
        "name": profile.get("name"),
        "picture": profile.get("picture"),
        "role": "user",
        "auth_providers": ["google"],
        "email_verified": True,   # Google verified the email for us
        "phone_verified": False,
        "created_at": now,
        "updated_at": now,
    }
    await _users_col.insert_one(dict(doc))
    return doc


@router.post("/register")
async def register(body: RegisterBody, response: Response):
    email = body.email.lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "Invalid email")
    if await _users_col.find_one({"email": email}):
        raise HTTPException(409, "Email already registered — please sign in instead")

    uid = f"user_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": uid,
        "email": email,
        "name": (body.name or email.split("@")[0])[:80],
        "picture": None,
        "role": "user",
        "auth_providers": ["email"],
        "password_hash": hash_password(body.password),
        "created_at": now,
        "updated_at": now,
    }
    await _users_col.insert_one(dict(doc))
    # Record pending referral if the user provided a code
    if body.referred_by:
        try:
            import referrals as _refs
            await _refs.record_pending(body.referred_by.strip(), uid)
        except Exception:
            pass
    # Launch-promo: auto-grant a free trial on first login/signup
    try:
        import licenses as _lic
        await _lic.auto_grant_promo_trial(uid)
    except Exception:
        pass
    access = create_access_token(uid, email)
    refresh = create_refresh_token(uid)
    _set_auth_cookies(response, access, refresh)
    return _user_public(doc)


@router.post("/login")
async def login(body: LoginBody, response: Response):
    email = body.email.lower()
    user = await _users_col.find_one({"email": email})
    if not user or not user.get("password_hash"):
        raise HTTPException(401, "Invalid email or password")
    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    access = create_access_token(user["user_id"], email)
    refresh = create_refresh_token(user["user_id"])
    _set_auth_cookies(response, access, refresh)
    # Launch-promo: auto-grant the free trial if this is truly the user's
    # first login (no prior license history at all).
    try:
        import licenses as _lic
        await _lic.auto_grant_promo_trial(user["user_id"])
    except Exception:
        pass
    return _user_public(user)


@router.post("/session")
async def emergent_session_exchange(body: SessionExchangeBody, response: Response):
    """Called by the frontend AuthCallback after a Google redirect.
    Exchanges the one-time session_id for a persistent session_token cookie."""
    profile = await _emergent_lookup_session(body.session_id)
    user = await _upsert_user_from_google(profile)
    session_token = profile.get("session_token")
    if not session_token:
        raise HTTPException(500, "Emergent did not return a session_token")

    expires_at = datetime.now(timezone.utc) + timedelta(days=EMERGENT_SESSION_DAYS)
    await _sessions_col.update_one(
        {"session_token": session_token},
        {"$set": {
            "user_id": user["user_id"],
            "session_token": session_token,
            "email": user["email"],
            "expires_at": expires_at,
            "source": "emergent",
            "created_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )
    _set_session_cookie(response, session_token)
    # Launch-promo: auto-grant the free trial on first Google sign-in too.
    try:
        import licenses as _lic
        await _lic.auto_grant_promo_trial(user["user_id"])
    except Exception:
        pass
    return _user_public(user)


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return _user_public(user)


@router.post("/logout")
async def logout(request: Request, response: Response):
    # Best-effort: remove any emergent session_token record
    st = request.cookies.get("session_token")
    if st and _sessions_col is not None:
        await _sessions_col.delete_one({"session_token": st})
    _clear_all_auth_cookies(response)
    return {"ok": True}


@router.post("/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(401, "No refresh token")
    payload = _decode_jwt(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid refresh token")
    user = await _user_by_id(payload["sub"])
    if not user:
        raise HTTPException(401, "User not found")
    access = create_access_token(user["user_id"], user["email"])
    response.set_cookie(
        "access_token", access, httponly=True, secure=True, samesite="none",
        max_age=ACCESS_TOKEN_MIN * 60, path="/",
    )
    return {"ok": True}


# ---------- Startup helpers ----------
async def ensure_indexes(users_col, sessions_col) -> None:
    await users_col.create_index("email", unique=True)
    await users_col.create_index("user_id", unique=True)
    await sessions_col.create_index("session_token", unique=True)
    await sessions_col.create_index("expires_at", expireAfterSeconds=0)


async def seed_admin(users_col) -> Optional[dict]:
    email = (os.environ.get("ADMIN_EMAIL") or "").lower().strip()
    password = os.environ.get("ADMIN_PASSWORD")
    if not email or not password:
        return None
    existing = await users_col.find_one({"email": email})
    if not existing:
        doc = {
            "user_id": f"user_{uuid.uuid4().hex[:12]}",
            "email": email,
            "name": "Admin",
            "picture": None,
            "role": "admin",
            "auth_providers": ["email"],
            "password_hash": hash_password(password),
            "created_at": datetime.now(timezone.utc),
        }
        await users_col.insert_one(doc)
        logger.info("Seeded admin user: %s", email)
        return doc
    elif existing.get("password_hash") and not verify_password(password, existing["password_hash"]):
        await users_col.update_one(
            {"email": email},
            {"$set": {"password_hash": hash_password(password), "role": "admin"}},
        )
        logger.info("Updated admin password: %s", email)
    return existing
