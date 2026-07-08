"""Shared fixtures for Story-to-Film backend tests."""
import os
import requests
import pytest
from dotenv import load_dotenv

# Load backend env for direct DB access when necessary
load_dotenv("/app/backend/.env")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    # frontend .env has the public URL
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.strip().split("=", 1)[1]
BASE_URL = (BASE_URL or "").rstrip("/")

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@aipillu.studio")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "aipilluAdmin@2026")


def _login_admin_and_get_cookies() -> dict:
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=15,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Admin login failed ({r.status_code}): {r.text}")
    return dict(r.cookies.items())


@pytest.fixture(scope="session", autouse=True)
def _autoauth_all_requests():
    """Session-wide monkey-patch: every call to `requests.get/post/...` targeting
    our BASE_URL automatically carries the admin session cookies. This lets
    the existing 80+ tests continue to work unchanged after the 2026-07-07 auth
    rollout — while /api/auth/* tests can still register/login their own users
    (their responses just add more cookies on top; the admin ones are ignored).
    """
    cookies = _login_admin_and_get_cookies()

    # Reset admin's "free tier used" flag at the start of a test session so
    # /claim-free tests can run repeatedly against the same seeded admin user.
    try:
        from pymongo import MongoClient
        _mc = MongoClient(os.environ["MONGO_URL"])
        _mc[os.environ["DB_NAME"]]["projects"].update_many(
            {"owner_email": ADMIN_EMAIL.lower(), "free_granted": True},
            {"$set": {"free_granted": False}},
        )
        _mc.close()
    except Exception:
        pass

    original_request = requests.api.request

    def patched(method, url, **kwargs):
        if BASE_URL and isinstance(url, str) and url.startswith(BASE_URL):
            existing = kwargs.get("cookies")
            if existing is None:
                kwargs["cookies"] = dict(cookies)
            elif isinstance(existing, dict):
                merged = dict(cookies)
                merged.update(existing)
                kwargs["cookies"] = merged
            # else: leave alone (CookieJar etc — tests can override deliberately)
        return original_request(method, url, **kwargs)

    requests.api.request = patched
    yield
    requests.api.request = original_request


@pytest.fixture(autouse=True)
def _reset_admin_free_tier_between_tests():
    """Between every test, clear the seeded admin's `free_granted` projects so
    /claim-free scenarios can be exercised across multiple tests in the same run.
    Cheap: one small MongoDB update. Runs BEFORE each test."""
    try:
        from pymongo import MongoClient
        mc = MongoClient(os.environ["MONGO_URL"])
        try:
            mc[os.environ["DB_NAME"]]["projects"].update_many(
                {"owner_email": ADMIN_EMAIL.lower(), "free_granted": True},
                {"$set": {"free_granted": False}},
            )
        finally:
            mc.close()
    except Exception:
        pass


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL

    yield


@pytest.fixture
def api_client():
    """Session pre-authenticated as the seeded admin."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    for k, v in _login_admin_and_get_cookies().items():
        s.cookies.set(k, v)
    return s


@pytest.fixture
def anon_client():
    """Anonymous session with no cookies. Use to verify 401 gating."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s
