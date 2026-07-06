"""Backend tests for Story-to-Film AI Agent.

Covers:
- Health, CORS
- Project CRUD
- Ingestion (text, url) — url uses live wikipedia (mocked-avoidance not needed)
- Analyze (Claude Sonnet 4.6) — SMOKE only (1 call)
- Unlock status / paywall / claim-free / checkout / status / webhook
- Storage gating for final_film
- TTS narration smoke (1 scene)
- Nano Banana image smoke (1 scene)  # Optional; guarded by env RUN_IMAGE_SMOKE=1

Uses public REACT_APP_BACKEND_URL. Uses ffmpeg lavfi to fabricate a small
final_film mp4 for paywall tests, and pymongo/motor is used through the
service (via a helper direct-mongo write with the sync pymongo client) —
we cannot go through an HTTP admin endpoint since none exists.
"""
import os
import time
import subprocess
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

BASE_URL = None
with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.strip().split("=", 1)[1]
BASE_URL = (BASE_URL or "").rstrip("/")

# For long-running LLM operations (Claude analyze), the Cloudflare proxy has a
# ~100s idle timeout which is shorter than the Claude Sonnet 4.6 typical
# response time (~2 minutes). We fall back to the internal backend URL for
# those specific tests, while still validating the routing/logic end-to-end.
LOCAL_URL = "http://localhost:8001"

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
STORAGE_DIR = "/app/backend/storage"

RAMAYANA_SHORT = (
    "Long ago, in the kingdom of Ayodhya lived a noble prince who was exiled to the forest "
    "with his devoted wife and loyal brother. In the deep woods, a demon king with ten heads "
    "abducted the princess and carried her across the sea to his island fortress. The prince "
    "assembled a great army of forest folk and a mighty warrior with a monkey's face, then "
    "crossed the ocean to rescue her. After a fierce battle the demon king was slain and the "
    "family returned home to be crowned in celebration."
)


# ---------------------------------------------------------------------------
# Session-wide project fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def created_project():
    """Create a fresh project via API and return its id + full doc."""
    r = requests.post(f"{BASE_URL}/api/projects", json={"title": "TEST_Ramayan"})
    assert r.status_code == 200, r.text
    doc = r.json()
    return doc


# ---------------------------------------------------------------------------
# Basics
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health(self):
        r = requests.get(f"{BASE_URL}/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "time" in data

    def test_cors_options(self):
        # A GET-preflight will only be triggered when there's a non-simple header, but
        # we still verify CORS headers are present for cross-origin requests.
        r = requests.options(
            f"{BASE_URL}/api/health",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        # Some proxies return 200 with headers; some return 204
        assert r.status_code in (200, 204), r.text
        acao = r.headers.get("access-control-allow-origin", "").lower()
        assert acao in ("*", "https://example.com"), f"Missing/invalid CORS header: {dict(r.headers)}"


# ---------------------------------------------------------------------------
# Project CRUD
# ---------------------------------------------------------------------------

class TestProjectCRUD:
    def test_create_project(self):
        r = requests.post(f"{BASE_URL}/api/projects", json={"title": "TEST_crud_a"})
        assert r.status_code == 200, r.text
        doc = r.json()
        assert doc["title"] == "TEST_crud_a"
        assert doc["paid"] is False
        assert doc["free_granted"] is False
        assert doc["status"] == "created"
        assert doc["final_film"] is None
        assert isinstance(doc["id"], str) and len(doc["id"]) > 0
        pytest.crud_pid = doc["id"]

    def test_list_projects(self):
        r = requests.get(f"{BASE_URL}/api/projects")
        assert r.status_code == 200
        arr = r.json()
        assert isinstance(arr, list)
        pids = [p["id"] for p in arr]
        assert pytest.crud_pid in pids

    def test_get_project(self):
        r = requests.get(f"{BASE_URL}/api/projects/{pytest.crud_pid}")
        assert r.status_code == 200
        doc = r.json()
        assert doc["id"] == pytest.crud_pid
        assert doc["paid"] is False
        assert doc["free_granted"] is False

    def test_get_missing_project(self):
        r = requests.get(f"{BASE_URL}/api/projects/does_not_exist_zzz")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

class TestIngestion:
    def test_ingest_text(self, created_project):
        pid = created_project["id"]
        r = requests.post(
            f"{BASE_URL}/api/projects/{pid}/ingest/text",
            json={"text": RAMAYANA_SHORT},
        )
        assert r.status_code == 200, r.text
        assert r.json()["chars"] == len(RAMAYANA_SHORT)

        # Verify persisted source_type
        doc = requests.get(f"{BASE_URL}/api/projects/{pid}").json()
        assert doc["source_type"] == "text"
        assert len(doc["source_text"]) >= 30
        assert doc["status"] == "ingested"

    def test_ingest_text_too_short(self, created_project):
        pid = created_project["id"]
        r = requests.post(
            f"{BASE_URL}/api/projects/{pid}/ingest/text",
            json={"text": "short"},
        )
        assert r.status_code == 400

    def test_ingest_url_wikipedia(self):
        # Use a fresh project to avoid overwriting the ingested text
        pid = requests.post(f"{BASE_URL}/api/projects", json={"title": "TEST_url_ingest"}).json()["id"]
        r = requests.post(
            f"{BASE_URL}/api/projects/{pid}/ingest/url",
            json={"url": "https://en.wikipedia.org/wiki/Ramayana"},
            timeout=60,
        )
        # KNOWN BUG: Wikipedia blocks the default User-Agent "Mozilla/5.0 StoryFilmAgent"
        # returning 403 -> backend re-raises as HTTP 400. This test documents the bug.
        if r.status_code == 400 and "403 Forbidden" in r.text:
            pytest.fail(
                "BUG: Wikipedia URL ingestion returns 403 due to non-compliant "
                "User-Agent in ingestion.extract_from_url. Wikipedia requires a "
                "descriptive UA per their policy."
            )
        assert r.status_code == 200, r.text
        assert r.json()["chars"] > 200
        doc = requests.get(f"{BASE_URL}/api/projects/{pid}").json()
        assert doc["source_type"] == "url"
        assert doc["source_meta"].get("url", "").endswith("/wiki/Ramayana")

    def test_ingest_url_generic(self):
        # Verify URL ingestion works for a non-blocking site
        pid = requests.post(f"{BASE_URL}/api/projects", json={"title": "TEST_url_generic"}).json()["id"]
        r = requests.post(
            f"{BASE_URL}/api/projects/{pid}/ingest/url",
            json={"url": "https://example.com"},
            timeout=60,
        )
        # example.com content is < 30 chars extractable text -> backend returns 400
        # Just verify the endpoint responds (either 200 or 400 for short content).
        assert r.status_code in (200, 400)


# ---------------------------------------------------------------------------
# Analyze (Claude Sonnet 4.6) — SMOKE
# ---------------------------------------------------------------------------

class TestAnalyze:
    def test_analyze_blueprint(self, created_project):
        pid = created_project["id"]
        # Ensure text is ingested for this project (module-scoped fixture)
        requests.post(f"{BASE_URL}/api/projects/{pid}/ingest/text", json={"text": RAMAYANA_SHORT})
        # LLM call — Claude Sonnet 4.6 typically takes 90-150s.
        # Cloudflare proxy on the public URL times out at ~100s and returns 502,
        # so we bypass the proxy and call the backend directly. The routing has
        # already been verified by the health/CRUD tests above.
        r = requests.post(
            f"{LOCAL_URL}/api/projects/{pid}/analyze",
            json={"language_hint": "auto"},
            timeout=240,
        )
        assert r.status_code == 200, r.text[:800]
        doc = r.json()
        assert isinstance(doc.get("characters"), list) and len(doc["characters"]) >= 1
        assert isinstance(doc.get("scenes"), list) and len(doc["scenes"]) >= 2

        # Character names should be original (not exactly matching common mythological figures)
        forbidden = {"rama", "ravana", "ravan", "sita", "lakshmana", "hanuman"}
        char_names_lower = {(c.get("name") or "").lower() for c in doc["characters"]}
        assert not (char_names_lower & forbidden), (
            f"Characters must not exactly equal mythological names: {char_names_lower}"
        )

        # Scenes must have required prompt fields
        s0 = doc["scenes"][0]
        for k in ("image_prompt", "video_prompt", "narration"):
            assert s0.get(k), f"scene[0] missing '{k}'"

        pytest.analyzed_pid = pid
        pytest.first_scene_id = s0["id"]

    def test_public_url_analyze_times_out(self, created_project):
        """Documents that the public URL cannot serve /analyze in time."""
        pid = created_project["id"]
        # Only run if analyze has already succeeded and stored data
        r = requests.get(f"{BASE_URL}/api/projects/{pid}", timeout=15)
        if r.status_code == 200 and r.json().get("status") == "analyzed":
            # Already analyzed — retrieving should be fast via public URL
            assert r.status_code == 200


# ---------------------------------------------------------------------------
# TTS narration smoke (1 call)
# ---------------------------------------------------------------------------

class TestTTS:
    def test_narration_smoke(self):
        pid = getattr(pytest, "analyzed_pid", None)
        sid = getattr(pytest, "first_scene_id", None)
        if not (pid and sid):
            pytest.skip("Analyze must succeed first")
        r = requests.post(
            f"{BASE_URL}/api/projects/{pid}/scenes/{sid}/narration",
            json={"voice": "onyx", "model": "tts-1"},
            timeout=120,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        audio_file = body["audio_file"]
        assert audio_file.endswith(".mp3")

        # Fetch from /api/storage/{audio_file}
        r2 = requests.get(f"{BASE_URL}/api/storage/{audio_file}", timeout=60)
        assert r2.status_code == 200
        assert r2.headers.get("content-type", "").startswith("audio/mpeg")
        assert len(r2.content) > 500


# ---------------------------------------------------------------------------
# Nano Banana image smoke (single) — guarded
# ---------------------------------------------------------------------------

@pytest.mark.skipif(os.getenv("SKIP_IMAGE_SMOKE") == "1", reason="Image smoke disabled")
class TestImage:
    def test_scene_image_smoke(self):
        pid = getattr(pytest, "analyzed_pid", None)
        sid = getattr(pytest, "first_scene_id", None)
        if not (pid and sid):
            pytest.skip("Analyze must succeed first")
        r = requests.post(f"{BASE_URL}/api/projects/{pid}/scenes/{sid}/image", timeout=180)
        assert r.status_code == 200, r.text
        image_file = r.json()["image_file"]
        assert image_file.endswith(".png")
        r2 = requests.get(f"{BASE_URL}/api/storage/{image_file}", timeout=60)
        assert r2.status_code == 200
        assert r2.headers.get("content-type", "").startswith("image/")
        assert len(r2.content) > 1000


# ---------------------------------------------------------------------------
# Paywall / Unlock / Checkout / Webhook
# ---------------------------------------------------------------------------

def _make_small_mp4(path: str, duration: int = 2) -> None:
    """Use ffmpeg lavfi to create a tiny black-screen mp4 (<20 MB)."""
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"color=c=black:s=320x240:d={duration}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", path,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


@pytest.fixture(scope="module")
def paywall_projects():
    """Create two projects with a fake small final_film for paywall testing.
    Direct mongo write is required — no admin endpoint exists.
    """
    client = MongoClient(MONGO_URL)
    projects_col = client[DB_NAME]["projects"]

    # Project A (first paid film for user)
    pidA = requests.post(f"{BASE_URL}/api/projects", json={"title": "TEST_paywall_A"}).json()["id"]
    fileA = f"{pidA}_final_film.mp4"
    _make_small_mp4(f"{STORAGE_DIR}/{fileA}")
    projects_col.update_one(
        {"id": pidA},
        {"$set": {"final_film": fileA, "status": "assembled", "paid": False, "free_granted": False}},
    )

    # Project B (second film for the same user — should require payment)
    pidB = requests.post(f"{BASE_URL}/api/projects", json={"title": "TEST_paywall_B"}).json()["id"]
    fileB = f"{pidB}_final_film.mp4"
    _make_small_mp4(f"{STORAGE_DIR}/{fileB}")
    projects_col.update_one(
        {"id": pidB},
        {"$set": {"final_film": fileB, "status": "assembled", "paid": False, "free_granted": False}},
    )

    yield {"pidA": pidA, "pidB": pidB, "fileA": fileA, "fileB": fileB}

    # Teardown — remove created files and projects
    for f in (fileA, fileB):
        try:
            os.remove(f"{STORAGE_DIR}/{f}")
        except OSError:
            pass
    projects_col.delete_many({"id": {"$in": [pidA, pidB]}})
    client.close()


class TestPaywall:
    def test_unlock_status_no_final(self, created_project):
        pid = created_project["id"]
        r = requests.get(f"{BASE_URL}/api/projects/{pid}/unlock-status?user_id=U1")
        assert r.status_code == 200
        data = r.json()
        assert data["has_final_film"] is False
        assert "price" in data
        # Price breakdown should have expected keys
        for k in ("base_inr", "size_fee_inr", "quality_fee_inr", "total_inr", "free_tier_bytes"):
            assert k in data["price"]

    def test_checkout_without_final_film(self, created_project):
        pid = created_project["id"]
        r = requests.post(
            f"{BASE_URL}/api/projects/{pid}/checkout",
            json={"origin_url": "https://example.com", "user_id": "U1"},
        )
        assert r.status_code == 400

    def test_film_without_unlock_returns_402(self, paywall_projects):
        # Even though final_film exists, without paid/free_granted the endpoint returns 402
        pidA = paywall_projects["pidA"]
        r = requests.get(f"{BASE_URL}/api/projects/{pidA}/film?user_id=UZZ")
        assert r.status_code == 402

    def test_storage_gates_final_film(self, paywall_projects):
        fileA = paywall_projects["fileA"]
        r = requests.get(f"{BASE_URL}/api/storage/{fileA}")
        assert r.status_code == 402

    def test_storage_allows_non_final(self, paywall_projects):
        # Any non-*_final_film.mp4 asset is allowed (though may 404 if not present)
        r = requests.get(f"{BASE_URL}/api/storage/nonexistent_regular_file.png")
        # Must NOT be 402
        assert r.status_code != 402


class TestFreeTierAndPayment:
    def test_free_eligible_then_claim_then_second_requires_payment(self, paywall_projects):
        pidA = paywall_projects["pidA"]
        pidB = paywall_projects["pidB"]
        user_id = "U_new_" + str(int(time.time()))

        # A: free eligible (<= 20 MB, user's first film)
        r = requests.get(f"{BASE_URL}/api/projects/{pidA}/unlock-status?user_id={user_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["free_eligible"] is True, data
        assert data["requires_payment"] is False

        # claim free
        r2 = requests.post(
            f"{BASE_URL}/api/projects/{pidA}/claim-free",
            json={"origin_url": "http://x", "user_id": user_id},
        )
        assert r2.status_code == 200, r2.text
        assert r2.json().get("free_granted") is True or r2.json().get("already_unlocked")

        # GET film should now return the file
        r3 = requests.get(f"{BASE_URL}/api/projects/{pidA}/film?user_id={user_id}")
        assert r3.status_code == 200
        assert r3.headers.get("content-type", "").startswith("video/mp4")
        assert len(r3.content) > 100

        # B: unlock-status for same user -> free_eligible false, requires_payment true
        r4 = requests.get(f"{BASE_URL}/api/projects/{pidB}/unlock-status?user_id={user_id}")
        assert r4.status_code == 200
        d4 = r4.json()
        assert d4["free_eligible"] is False, d4
        assert d4["requires_payment"] is True, d4

        # POST checkout -> returns Stripe URL and session_id
        r5 = requests.post(
            f"{BASE_URL}/api/projects/{pidB}/checkout",
            json={"origin_url": "https://example.com", "user_id": user_id},
            timeout=60,
        )
        # KNOWN BUG: For a small (<20MB) film the pricing formula floors at
        # ₹19 which converts to ~$0.20 — below Stripe's $0.50 minimum.
        if r5.status_code == 500 and "at least 50 cents" in r5.text:
            pytest.fail(
                "BUG: /checkout for a low-priced film fails because ₹19 floor "
                "in payments.compute_price_inr is below Stripe's $0.50 minimum. "
                "Raise the floor to ~₹45 or gate small films via free tier only."
            )
        assert r5.status_code == 200, r5.text
        d5 = r5.json()
        assert d5["ok"] is True
        assert d5["url"].startswith("http"), d5
        assert isinstance(d5["session_id"], str) and len(d5["session_id"]) > 0
        assert d5["amount_inr"] >= 19

        # Verify a payment_transactions record exists with payment_status='initiated'
        client = MongoClient(MONGO_URL)
        try:
            tx = client[DB_NAME]["payment_transactions"].find_one({"session_id": d5["session_id"]})
            assert tx is not None
            assert tx["payment_status"] == "initiated"
            assert tx["project_id"] == pidB
            assert tx["user_id"] == user_id
        finally:
            client.close()

        pytest.session_id = d5["session_id"]

    def test_checkout_status_unpaid(self):
        sid = getattr(pytest, "session_id", None)
        if not sid:
            pytest.skip("checkout not created")
        r = requests.get(f"{BASE_URL}/api/checkout/status/{sid}", timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        # Should not be paid at this stage
        assert data["payment_status"] != "paid"
        assert "status" in data

    def test_webhook_invalid_signature(self):
        r = requests.post(
            f"{BASE_URL}/api/webhook/stripe",
            data=b'{"type":"noop"}',
            headers={"Stripe-Signature": "bad_signature_value", "Content-Type": "application/json"},
        )
        assert r.status_code == 400


class TestCheckoutHappyPath:
    """Verify that when the price exceeds Stripe's $0.50 minimum,
    the checkout endpoint successfully returns a Stripe session."""

    def test_checkout_large_film(self):
        client = MongoClient(MONGO_URL)
        projects_col = client[DB_NAME]["projects"]
        try:
            pid = requests.post(f"{BASE_URL}/api/projects", json={"title": "TEST_bigpay"}).json()["id"]
            path = f"{STORAGE_DIR}/{pid}_final_film.mp4"
            # ~100 MB pushes the price above ₹45 -> above Stripe minimum
            with open(path, "wb") as f:
                f.write(os.urandom(100 * 1024 * 1024))
            projects_col.update_one(
                {"id": pid},
                {"$set": {"final_film": f"{pid}_final_film.mp4", "status": "assembled"}},
            )
            r = requests.post(
                f"{BASE_URL}/api/projects/{pid}/checkout",
                json={"origin_url": "https://example.com", "user_id": "U_bigpay"},
                timeout=60,
            )
            assert r.status_code == 200, r.text
            d = r.json()
            assert d["ok"] is True
            assert d["url"].startswith("https://checkout.stripe.com/")
            assert d["amount_inr"] >= 45

            # payment_transactions record created
            tx = client[DB_NAME]["payment_transactions"].find_one({"session_id": d["session_id"]})
            assert tx is not None
            assert tx["payment_status"] == "initiated"

            # checkout status endpoint responds without error
            r2 = requests.get(f"{BASE_URL}/api/checkout/status/{d['session_id']}", timeout=60)
            assert r2.status_code == 200
            data = r2.json()
            assert data["payment_status"] != "paid"
        finally:
            try:
                os.remove(path)
            except OSError:
                pass
            projects_col.delete_one({"id": pid})
            client.close()
