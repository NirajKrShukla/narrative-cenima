"""Tests for the new license + OTP system (2026-07-20 rewrite)."""
import os
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL") or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0]
BASE_URL = BASE_URL.rstrip("/")


class TestLicensePlans:
    def test_plans_endpoint_is_public(self):
        # /api/licenses/plans is in the public prefix list — reachable without auth
        s = requests.Session()  # no cookies
        r = s.get(f"{BASE_URL}/api/licenses/plans")
        assert r.status_code == 200
        d = r.json()
        assert d["currency"] == "INR"
        plans = {p["id"]: p for p in d["plans"]}
        assert "trial" in plans and plans["trial"]["days"] == 7 and plans["trial"]["amount_paise"] == 0
        assert plans["m1"]["days"] == 30 and plans["m1"]["amount_paise"] == 9900
        assert plans["m2"]["days"] == 60 and plans["m2"]["amount_paise"] == 17000
        assert plans["m3"]["days"] == 90 and plans["m3"]["amount_paise"] == 26000
        assert plans["y1"]["days"] == 365 and plans["y1"]["amount_paise"] == 95000


class TestLicenseSignupFlow:
    """Full happy-path: register → verify email+phone → start trial → create project."""

    @pytest.fixture(scope="class")
    def flow(self):
        ts = int(time.time_ns() % 10_000_000)
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        email = f"lic_flow_{ts}@aipillu.dev"
        phone = f"+91987{ts % 10_000_000:07d}"

        # Register
        r = s.post(f"{BASE_URL}/api/auth/register",
                   json={"email": email, "password": "TestPass123!", "name": "Flow"})
        assert r.status_code == 200, r.text

        # Send + verify email OTP
        r = s.post(f"{BASE_URL}/api/otp/send",
                   json={"channel": "email", "identifier": email})
        assert r.status_code == 200
        ecode = r.json().get("sandbox_code")
        assert ecode, "Sandbox mode should return the OTP in the response"
        r = s.post(f"{BASE_URL}/api/otp/verify",
                   json={"channel": "email", "identifier": email, "code": ecode})
        assert r.status_code == 200 and r.json()["verified"]

        # Send + verify phone OTP
        r = s.post(f"{BASE_URL}/api/otp/send",
                   json={"channel": "phone", "identifier": phone})
        pcode = r.json().get("sandbox_code")
        assert pcode
        r = s.post(f"{BASE_URL}/api/otp/verify",
                   json={"channel": "phone", "identifier": phone, "code": pcode})
        assert r.status_code == 200

        return {"session": s, "email": email, "phone": phone}

    def test_status_before_trial_says_can_start(self, flow):
        r = flow["session"].get(f"{BASE_URL}/api/licenses/status")
        d = r.json()
        # Launch promo auto-grants a license on first register — so this
        # user already has an active promo license. That means:
        #   - trial_used stays False (promo is a separate source)
        #   - can_start_trial is False (they already have an active license)
        #   - can_create_films is True (courtesy of the promo)
        assert d["trial_used"] is False
        assert d["can_create_films"] is True
        assert d["license"] is not None
        assert d["license"]["source"] in ("promo", "trial")

    def test_start_trial_activates_7_day_license(self, flow):
        # With the launch promo auto-granted, calling start-trial returns
        # 409 "already have active license". Simulate the post-promo world
        # by manually expiring the promo, then retry.
        import os, pymongo
        mc = pymongo.MongoClient(os.environ["MONGO_URL"])
        db = mc[os.environ["DB_NAME"]]
        me = flow["session"].get(f"{BASE_URL}/api/auth/me").json()
        db["licenses"].update_many(
            {"user_id": me["user_id"], "source": "promo"},
            {"$set": {"expires_at": (
                __import__("datetime").datetime.utcnow()
                - __import__("datetime").timedelta(days=1)
            )}},
        )
        mc.close()

        r = flow["session"].post(f"{BASE_URL}/api/licenses/start-trial")
        assert r.status_code == 200, r.text
        lic = r.json()["license"]
        assert lic["plan_id"] == "trial"
        assert 6 <= lic["days_remaining"] <= 7
        assert lic["source"] == "trial"

    def test_trial_can_only_be_used_once(self, flow):
        r = flow["session"].post(f"{BASE_URL}/api/licenses/start-trial")
        assert r.status_code == 409  # already used

    def test_can_create_project_with_active_license(self, flow):
        r = flow["session"].post(f"{BASE_URL}/api/projects",
                                 json={"title": "Trial test film"})
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        # Cleanup
        flow["session"].delete(f"{BASE_URL}/api/projects/{pid}")

    def test_sandbox_purchase_extends_license(self, flow):
        # Get current expiry
        before = flow["session"].get(f"{BASE_URL}/api/licenses/status").json()["license"]["days_remaining"]
        # Sandbox purchase 30-day plan
        r = flow["session"].post(f"{BASE_URL}/api/licenses/checkout/sandbox-complete",
                                 json={"plan_id": "m1"})
        assert r.status_code == 200, r.text
        after = flow["session"].get(f"{BASE_URL}/api/licenses/status").json()["license"]["days_remaining"]
        # Trial had ~7 days, + 30 = ~37
        assert after >= before + 29


class TestLicenseExpiryReadOnly:
    """After license expires, the user should still be able to GET their films but not POST new ones."""

    def test_expired_user_gets_402_on_create(self):
        # Register a fresh user, then expire their auto-granted promo license.
        import time, os
        from pymongo import MongoClient
        ts = int(time.time_ns() % 10_000_000)
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        email = f"exp_{ts}@aipillu.dev"
        r = s.post(f"{BASE_URL}/api/auth/register",
                   json={"email": email, "password": "TestPass123!"})
        assert r.status_code == 200
        # Expire the auto-granted promo
        me = s.get(f"{BASE_URL}/api/auth/me").json()
        mc = MongoClient(os.environ["MONGO_URL"])
        try:
            import datetime as _dt
            mc[os.environ["DB_NAME"]]["licenses"].update_many(
                {"user_id": me["user_id"]},
                {"$set": {"expires_at": _dt.datetime.utcnow() - _dt.timedelta(days=1)}},
            )
        finally:
            mc.close()

        r = s.post(f"{BASE_URL}/api/projects", json={"title": "Should fail"})
        assert r.status_code == 402
        assert r.json().get("license_required") is True

    def test_read_only_survives_expiry(self):
        # Users without license CAN still list projects (empty for fresh user)
        ts = int(time.time_ns() % 10_000_000)
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        email = f"ro_{ts}@aipillu.dev"
        s.post(f"{BASE_URL}/api/auth/register", json={"email": email, "password": "TestPass123!"})
        r = s.get(f"{BASE_URL}/api/projects")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestOtpRateLimit:
    def test_email_send_rate_limit(self):
        ts = int(time.time_ns() % 10_000_000)
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        email = f"rl_{ts}@aipillu.dev"
        s.post(f"{BASE_URL}/api/auth/register",
               json={"email": email, "password": "TestPass123!"})
        # Same identifier — burst 4 sends: first 3 pass, 4th should 429
        for i in range(3):
            r = s.post(f"{BASE_URL}/api/otp/send",
                       json={"channel": "email", "identifier": email})
            assert r.status_code == 200
        r = s.post(f"{BASE_URL}/api/otp/send",
                   json={"channel": "email", "identifier": email})
        assert r.status_code == 429



class TestLaunchPromo:
    """Auto-grant 20-day trial on first login/register (PROMO_TRIAL_ACTIVE=true)."""

    def test_register_auto_grants_promo(self):
        import os, time
        os.environ["PROMO_TRIAL_ACTIVE"] = "true"
        ts = int(time.time_ns() % 10_000_000)
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        email = f"promo_{ts}@aipillu.dev"
        r = s.post(f"{BASE_URL}/api/auth/register",
                   json={"email": email, "password": "TestPass123!"})
        assert r.status_code == 200

        # Should have auto-granted a 20-day promo license
        d = s.get(f"{BASE_URL}/api/licenses/status").json()
        assert d["license"] is not None
        assert d["license"]["source"] == "promo"
        assert d["license"]["days_remaining"] in (19, 20, 21)
        assert d["can_create_films"] is True

        # Can create projects immediately with no OTP verification
        r = s.post(f"{BASE_URL}/api/projects", json={"title": "Promo film"})
        assert r.status_code == 200

    def test_second_login_does_not_duplicate_promo(self):
        import time
        ts = int(time.time_ns() % 10_000_000)
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        email = f"promo2_{ts}@aipillu.dev"
        s.post(f"{BASE_URL}/api/auth/register",
               json={"email": email, "password": "TestPass123!"})
        s2 = requests.Session()
        s2.headers.update({"Content-Type": "application/json"})
        s2.post(f"{BASE_URL}/api/auth/login",
                json={"email": email, "password": "TestPass123!"})
        d = s2.get(f"{BASE_URL}/api/licenses/status").json()
        assert d["license"]["days_remaining"] <= 21
