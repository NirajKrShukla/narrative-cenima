"""Backend tests for Story-to-Film AI Agent (iteration_2 regression + P2).

Covers:
- Health / CORS / Project CRUD (basics)
- Ingestion (text, URL Wikipedia UA regression)
- Async analyze (regression: returns fast, poll to complete)
- Settings (voice/model/language/title validation)
- Batch pipeline (images -> narration -> kenburns) + progress
- Publish + Gallery + Tip (Stripe INR ≥ ₹49 floor)
- Paywall / Storage gating / Webhook signature
"""
import os
import time
import subprocess
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

# Public URL used for all functional tests
BASE_URL = None
with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.strip().split("=", 1)[1]
BASE_URL = (BASE_URL or "").rstrip("/")

# Local URL is no longer required for /analyze because it's async now,
# but retained as a fallback in case public proxy is slow.
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
# Helpers
# ---------------------------------------------------------------------------

def _make_small_mp4(path: str, duration: int = 2) -> None:
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"color=c=black:s=320x240:d={duration}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", path,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def _seed_blueprint(pid: str, n_scenes: int = 2) -> None:
    """Directly seed a blueprint + scenes for a project (avoids Claude spend)."""
    mc = MongoClient(MONGO_URL)
    try:
        scenes = []
        for i in range(1, n_scenes + 1):
            scenes.append({
                "id": f"scene_{i}",
                "title": f"Scene {i}",
                "description": f"A cinematic short scene number {i} depicting a hero's journey.",
                "image_prompt": f"Cinematic still, scene {i}, dramatic lighting.",
                "video_prompt": f"Wide cinematic shot, scene {i}, subtle camera movement.",
                "narration": f"This is the narration for scene number {i}. A brief moment in the film.",
                "image_file": None,
                "video_file": None,
                "audio_file": None,
                "final_file": None,
            })
        mc[DB_NAME]["projects"].update_one(
            {"id": pid},
            {"$set": {
                "blueprint": {
                    "title": "Seeded Blueprint",
                    "logline": "A short seeded film for testing.",
                    "genre": "drama",
                    "tone": "cinematic",
                    "visual_style": "cinematic film still",
                },
                "characters": [{"id": "char_1", "name": "Aria", "archetype": "hero",
                                 "description": "Brave protagonist.", "image_file": None}],
                "scenes": scenes,
                "status": "analyzed",
            }},
        )
    finally:
        mc.close()


# ---------------------------------------------------------------------------
# Session-wide project fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def created_project():
    r = requests.post(f"{BASE_URL}/api/projects", json={"title": "TEST_Ramayan"})
    assert r.status_code == 200, r.text
    return r.json()


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
        assert doc["voice"] == "onyx"
        assert doc["voice_model"] == "tts-1"
        assert doc["is_public"] is False
        pytest.crud_pid = doc["id"]

    def test_list_projects(self):
        r = requests.get(f"{BASE_URL}/api/projects")
        assert r.status_code == 200
        pids = [p["id"] for p in r.json()]
        assert pytest.crud_pid in pids

    def test_get_missing_project(self):
        r = requests.get(f"{BASE_URL}/api/projects/does_not_exist_zzz")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Ingestion — REGRESSION: Wikipedia UA
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

    def test_ingest_text_too_short(self, created_project):
        pid = created_project["id"]
        r = requests.post(
            f"{BASE_URL}/api/projects/{pid}/ingest/text",
            json={"text": "short"},
        )
        assert r.status_code == 400

    def test_ingest_url_wikipedia_regression(self):
        """REGRESSION: Wikipedia URL must succeed with descriptive UA (previously 403)."""
        pid = requests.post(f"{BASE_URL}/api/projects", json={"title": "TEST_url_ingest"}).json()["id"]
        r = requests.post(
            f"{BASE_URL}/api/projects/{pid}/ingest/url",
            json={"url": "https://en.wikipedia.org/wiki/Ramayana"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        assert r.json()["chars"] > 100
        doc = requests.get(f"{BASE_URL}/api/projects/{pid}").json()
        assert doc["source_type"] == "url"
        assert doc["source_meta"].get("url", "").endswith("/wiki/Ramayana")


# ---------------------------------------------------------------------------
# Analyze — REGRESSION: async return within seconds
# ---------------------------------------------------------------------------

class TestAsyncAnalyze:
    def test_analyze_returns_immediately(self, created_project):
        """REGRESSION: analyze must return {ok, status='analyzing'} within a few seconds."""
        pid = created_project["id"]
        # Make sure the source is ingested
        requests.post(f"{BASE_URL}/api/projects/{pid}/ingest/text", json={"text": RAMAYANA_SHORT})

        t0 = time.time()
        r = requests.post(
            f"{BASE_URL}/api/projects/{pid}/analyze",
            json={"language_hint": "auto"},
            timeout=15,
        )
        elapsed = time.time() - t0
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert data.get("status") == "analyzing"
        assert elapsed < 10, f"Analyze must return quickly, took {elapsed:.1f}s"

        # Poll until analyzed or error (max ~180s for Claude)
        deadline = time.time() + 200
        final_status = None
        while time.time() < deadline:
            time.sleep(5)
            g = requests.get(f"{BASE_URL}/api/projects/{pid}", timeout=15)
            if g.status_code != 200:
                continue
            st = g.json().get("status")
            if st in ("analyzed", "error"):
                final_status = st
                pytest.analyzed_doc = g.json()
                break
        assert final_status == "analyzed", f"Analyze did not finish successfully; status={final_status}"
        doc = pytest.analyzed_doc
        assert len(doc.get("characters") or []) >= 1
        assert len(doc.get("scenes") or []) >= 2
        pytest.analyzed_pid = pid
        pytest.first_scene_id = doc["scenes"][0]["id"]


# ---------------------------------------------------------------------------
# Settings endpoint
# ---------------------------------------------------------------------------

class TestSettings:
    @pytest.fixture(scope="class")
    def settings_pid(self):
        r = requests.post(f"{BASE_URL}/api/projects", json={"title": "TEST_settings"})
        return r.json()["id"]

    def test_patch_settings_valid(self, settings_pid):
        r = requests.patch(
            f"{BASE_URL}/api/projects/{settings_pid}/settings",
            json={"voice": "nova", "voice_model": "tts-1-hd", "language_hint": "hi", "title": "Test Title"},
        )
        assert r.status_code == 200, r.text
        d = requests.get(f"{BASE_URL}/api/projects/{settings_pid}").json()
        assert d["voice"] == "nova"
        assert d["voice_model"] == "tts-1-hd"
        assert d["language_hint"] == "hi"
        assert d["title"] == "Test Title"

    def test_patch_settings_invalid_voice(self, settings_pid):
        r = requests.patch(
            f"{BASE_URL}/api/projects/{settings_pid}/settings",
            json={"voice": "invalid"},
        )
        assert r.status_code == 400, r.text

    def test_patch_settings_invalid_voice_model(self, settings_pid):
        r = requests.patch(
            f"{BASE_URL}/api/projects/{settings_pid}/settings",
            json={"voice_model": "tts-mega"},
        )
        assert r.status_code == 400, r.text

    def test_patch_settings_missing_project(self):
        r = requests.patch(
            f"{BASE_URL}/api/projects/no_such_pid/settings",
            json={"voice": "nova"},
        )
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Narration uses project defaults
# ---------------------------------------------------------------------------

class TestNarrationDefaults:
    def test_narration_uses_project_defaults(self):
        """After PATCH voice=nova, narration WITHOUT voice param must use nova."""
        # Create project + seed blueprint
        pid = requests.post(f"{BASE_URL}/api/projects", json={"title": "TEST_narr_defaults"}).json()["id"]
        _seed_blueprint(pid, n_scenes=1)

        # Set defaults
        r = requests.patch(
            f"{BASE_URL}/api/projects/{pid}/settings",
            json={"voice": "nova", "voice_model": "tts-1"},
        )
        assert r.status_code == 200

        # Call narration WITHOUT voice param
        r2 = requests.post(
            f"{BASE_URL}/api/projects/{pid}/scenes/scene_1/narration",
            json={},
            timeout=120,
        )
        assert r2.status_code == 200, r2.text
        af = r2.json()["audio_file"]
        assert af.endswith(".mp3")

        # Confirm it can be fetched
        r3 = requests.get(f"{BASE_URL}/api/storage/{af}", timeout=60)
        assert r3.status_code == 200
        assert r3.headers.get("content-type", "").startswith("audio/mpeg")
        assert len(r3.content) > 500


# ---------------------------------------------------------------------------
# Batch pipeline
# ---------------------------------------------------------------------------

class TestBatch:
    @pytest.fixture(scope="class")
    def batch_pid(self):
        pid = requests.post(f"{BASE_URL}/api/projects", json={"title": "TEST_batch"}).json()["id"]
        _seed_blueprint(pid, n_scenes=2)
        return pid

    def test_batch_no_scenes_returns_400(self):
        pid = requests.post(f"{BASE_URL}/api/projects", json={"title": "TEST_batch_no_scenes"}).json()["id"]
        r = requests.post(
            f"{BASE_URL}/api/projects/{pid}/batch",
            json={"mode": "images", "video_type": "kenburns"},
        )
        assert r.status_code == 400
        assert "analyze" in r.text.lower() or "scenes" in r.text.lower()

    def test_batch_invalid_mode(self, batch_pid):
        r = requests.post(
            f"{BASE_URL}/api/projects/{batch_pid}/batch",
            json={"mode": "bogus", "video_type": "kenburns"},
        )
        assert r.status_code == 400

    def test_batch_invalid_video_type(self, batch_pid):
        r = requests.post(
            f"{BASE_URL}/api/projects/{batch_pid}/batch",
            json={"mode": "all", "video_type": "invalid"},
        )
        assert r.status_code == 400

    def test_batch_images_run_and_progress(self, batch_pid):
        r = requests.post(
            f"{BASE_URL}/api/projects/{batch_pid}/batch",
            json={"mode": "images", "video_type": "kenburns"},
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("ok") is True
        assert d.get("job_id")

        # Second concurrent call should return already_running
        r2 = requests.post(
            f"{BASE_URL}/api/projects/{batch_pid}/batch",
            json={"mode": "images", "video_type": "kenburns"},
        )
        assert r2.status_code == 200
        # If the first call is still running, second must indicate that.
        # If the first call was extremely fast and finished already, we allow a fresh job_id.
        j2 = r2.json()
        assert j2.get("already_running") is True or j2.get("job_id") is not None

        # Poll batch progress until done
        deadline = time.time() + 240
        last = None
        while time.time() < deadline:
            time.sleep(3)
            g = requests.get(f"{BASE_URL}/api/projects/{batch_pid}/batch", timeout=15)
            assert g.status_code == 200
            last = g.json()
            for k in ("running", "completed", "total", "current"):
                assert k in last, f"Missing key {k}"
            if last.get("running") is False:
                break
        assert last and last.get("running") is False, f"Batch never finished: {last}"

        # Every scene must now have image_file
        doc = requests.get(f"{BASE_URL}/api/projects/{batch_pid}").json()
        for s in doc.get("scenes") or []:
            assert s.get("image_file"), f"Scene {s['id']} missing image_file. Errors: {last.get('errors')}"

    def test_batch_narration_run(self, batch_pid):
        r = requests.post(
            f"{BASE_URL}/api/projects/{batch_pid}/batch",
            json={"mode": "narration", "video_type": "kenburns"},
        )
        assert r.status_code == 200, r.text
        deadline = time.time() + 240
        last = None
        while time.time() < deadline:
            time.sleep(3)
            g = requests.get(f"{BASE_URL}/api/projects/{batch_pid}/batch", timeout=15)
            last = g.json()
            if last.get("running") is False:
                break
        assert last and last.get("running") is False, f"Narration batch never finished: {last}"

        doc = requests.get(f"{BASE_URL}/api/projects/{batch_pid}").json()
        for s in doc.get("scenes") or []:
            assert s.get("audio_file"), f"Scene {s['id']} missing audio_file"

    def test_batch_kenburns_run(self, batch_pid):
        r = requests.post(
            f"{BASE_URL}/api/projects/{batch_pid}/batch",
            json={"mode": "kenburns", "video_type": "kenburns"},
        )
        assert r.status_code == 200, r.text
        deadline = time.time() + 240
        last = None
        while time.time() < deadline:
            time.sleep(3)
            g = requests.get(f"{BASE_URL}/api/projects/{batch_pid}/batch", timeout=15)
            last = g.json()
            if last.get("running") is False:
                break
        assert last and last.get("running") is False, f"Ken-Burns batch never finished: {last}"

        doc = requests.get(f"{BASE_URL}/api/projects/{batch_pid}").json()
        for s in doc.get("scenes") or []:
            vf = s.get("video_file")
            assert vf and vf.endswith("_kb.mp4"), f"Scene {s['id']} missing ken-burns video_file: {vf}"


# ---------------------------------------------------------------------------
# Paywall / Checkout — REGRESSION: ₹49 floor, Stripe accepts
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def paywall_projects():
    client = MongoClient(MONGO_URL)
    projects_col = client[DB_NAME]["projects"]

    pidA = requests.post(f"{BASE_URL}/api/projects", json={"title": "TEST_paywall_A"}).json()["id"]
    fileA = f"{pidA}_final_film.mp4"
    _make_small_mp4(f"{STORAGE_DIR}/{fileA}")
    projects_col.update_one(
        {"id": pidA},
        {"$set": {"final_film": fileA, "status": "assembled", "paid": False, "free_granted": False}},
    )

    pidB = requests.post(f"{BASE_URL}/api/projects", json={"title": "TEST_paywall_B"}).json()["id"]
    fileB = f"{pidB}_final_film.mp4"
    _make_small_mp4(f"{STORAGE_DIR}/{fileB}")
    projects_col.update_one(
        {"id": pidB},
        {"$set": {"final_film": fileB, "status": "assembled", "paid": False, "free_granted": False}},
    )

    yield {"pidA": pidA, "pidB": pidB, "fileA": fileA, "fileB": fileB}

    for f in (fileA, fileB):
        try:
            os.remove(f"{STORAGE_DIR}/{f}")
        except OSError:
            pass
    projects_col.delete_many({"id": {"$in": [pidA, pidB]}})
    client.close()


class TestPaywall:
    def test_storage_gates_final_film(self, paywall_projects):
        r = requests.get(f"{BASE_URL}/api/storage/{paywall_projects['fileA']}")
        assert r.status_code == 402

    def test_storage_allows_non_final(self):
        r = requests.get(f"{BASE_URL}/api/storage/nonexistent_regular_file.png")
        assert r.status_code != 402

    def test_film_without_unlock_returns_402(self, paywall_projects):
        r = requests.get(f"{BASE_URL}/api/projects/{paywall_projects['pidA']}/film?user_id=UZZ")
        assert r.status_code == 402


class TestStripeCheckoutFloor:
    def test_checkout_small_film_regression(self, paywall_projects):
        """REGRESSION: previously ₹19 floor caused Stripe 500 (below $0.50).
        Now floor is ₹49 — must return a valid Stripe URL."""
        pidA = paywall_projects["pidA"]
        pidB = paywall_projects["pidB"]
        user_id = "U_new_" + str(int(time.time()))

        # A: claim free
        r = requests.get(f"{BASE_URL}/api/projects/{pidA}/unlock-status?user_id={user_id}")
        assert r.status_code == 200 and r.json()["free_eligible"] is True

        r2 = requests.post(
            f"{BASE_URL}/api/projects/{pidA}/claim-free",
            json={"origin_url": "http://x", "user_id": user_id},
        )
        assert r2.status_code == 200

        # B: must require payment
        r3 = requests.get(f"{BASE_URL}/api/projects/{pidB}/unlock-status?user_id={user_id}")
        assert r3.status_code == 200
        assert r3.json()["requires_payment"] is True

        r4 = requests.post(
            f"{BASE_URL}/api/projects/{pidB}/checkout",
            json={"origin_url": "https://example.com", "user_id": user_id},
            timeout=60,
        )
        assert r4.status_code == 200, r4.text
        d = r4.json()
        assert d["ok"] is True
        assert d["url"].startswith("http")
        assert d["amount_inr"] >= 49  # regression: floor raised to ₹49
        pytest.checkout_session_id = d["session_id"]

    def test_checkout_status_unpaid(self):
        sid = getattr(pytest, "checkout_session_id", None)
        if not sid:
            pytest.skip("checkout not created")
        r = requests.get(f"{BASE_URL}/api/checkout/status/{sid}", timeout=60)
        assert r.status_code == 200
        assert r.json()["payment_status"] != "paid"

    def test_webhook_invalid_signature(self):
        r = requests.post(
            f"{BASE_URL}/api/webhook/stripe",
            data=b'{"type":"noop"}',
            headers={"Stripe-Signature": "bad_signature_value", "Content-Type": "application/json"},
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Gallery + Publish + Tip
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def published_project():
    """Create a project + fake mp4 + unlock (free) + publish."""
    client = MongoClient(MONGO_URL)
    projects_col = client[DB_NAME]["projects"]
    pid = requests.post(f"{BASE_URL}/api/projects", json={"title": "TEST_publish"}).json()["id"]
    fname = f"{pid}_final_film.mp4"
    _make_small_mp4(f"{STORAGE_DIR}/{fname}")
    projects_col.update_one(
        {"id": pid},
        {"$set": {
            "final_film": fname,
            "status": "assembled",
            "scenes": [{"id": "scene_1", "title": "S1", "image_file": None}],
            "blueprint": {"logline": "A tiny cinematic test."},
        }},
    )
    user_id = "U_pub_" + str(int(time.time()))
    yield {"pid": pid, "fname": fname, "user_id": user_id}
    try:
        os.remove(f"{STORAGE_DIR}/{fname}")
    except OSError:
        pass
    projects_col.delete_one({"id": pid})
    client.close()


class TestPublishGallery:
    def test_publish_unlocked_required(self, published_project):
        pid = published_project["pid"]
        r = requests.post(
            f"{BASE_URL}/api/projects/{pid}/publish",
            json={"is_public": True, "tip_vpa": "test@upi"},
        )
        assert r.status_code == 402

    def test_unlock_then_publish_and_gallery(self, published_project):
        pid = published_project["pid"]
        user_id = published_project["user_id"]

        r = requests.post(
            f"{BASE_URL}/api/projects/{pid}/claim-free",
            json={"origin_url": "http://x", "user_id": user_id},
        )
        assert r.status_code == 200, r.text

        r2 = requests.post(
            f"{BASE_URL}/api/projects/{pid}/publish",
            json={"is_public": True, "tip_vpa": "test@upi"},
        )
        assert r2.status_code == 200, r2.text
        assert r2.json()["is_public"] is True

        # GET gallery contains this pid
        g = requests.get(f"{BASE_URL}/api/gallery")
        assert g.status_code == 200
        arr = g.json()
        assert any(item["id"] == pid for item in arr)
        item = next(item for item in arr if item["id"] == pid)
        assert item["tip_vpa"] == "test@upi"
        assert item["title"] == "TEST_publish"
        assert "logline" in item

        # GET single gallery item and views increments
        s1 = requests.get(f"{BASE_URL}/api/gallery/{pid}").json()
        v1 = s1["views"]
        s2 = requests.get(f"{BASE_URL}/api/gallery/{pid}").json()
        assert s2["views"] > v1

        # Stream returns 200 video/mp4
        s = requests.get(f"{BASE_URL}/api/gallery/{pid}/stream", timeout=30)
        assert s.status_code == 200
        assert s.headers.get("content-type", "").startswith("video/mp4")

    def test_tip_valid_and_bounds(self, published_project):
        pid = published_project["pid"]

        # Below minimum
        r_lo = requests.post(
            f"{BASE_URL}/api/gallery/{pid}/tip",
            json={"amount_inr": 20, "origin_url": "https://x", "user_id": "U_tip"},
        )
        assert r_lo.status_code == 400

        # Above max
        r_hi = requests.post(
            f"{BASE_URL}/api/gallery/{pid}/tip",
            json={"amount_inr": 20000, "origin_url": "https://x", "user_id": "U_tip"},
        )
        assert r_hi.status_code == 400

        # Valid
        r_ok = requests.post(
            f"{BASE_URL}/api/gallery/{pid}/tip",
            json={"amount_inr": 99, "origin_url": "https://x", "user_id": "U_tip"},
            timeout=60,
        )
        assert r_ok.status_code == 200, r_ok.text
        d = r_ok.json()
        assert d["ok"] is True
        assert d["url"].startswith("http")
        assert isinstance(d["session_id"], str) and len(d["session_id"]) > 0
        pytest.tip_session_id = d["session_id"]
        pytest.tip_pid = pid

    def test_tip_status_unpaid_no_increment(self):
        sid = getattr(pytest, "tip_session_id", None)
        pid = getattr(pytest, "tip_pid", None)
        if not sid or not pid:
            pytest.skip("tip session not created")

        before = requests.get(f"{BASE_URL}/api/gallery/{pid}").json()
        r = requests.get(f"{BASE_URL}/api/tip/status/{sid}", timeout=60)
        assert r.status_code == 200
        assert r.json()["payment_status"] != "paid"
        after = requests.get(f"{BASE_URL}/api/gallery/{pid}").json()
        # tips_total_inr must NOT be incremented for unpaid session
        assert after["tips_total_inr"] == before["tips_total_inr"]

    def test_unpublish_removes_from_gallery(self, published_project):
        pid = published_project["pid"]
        r = requests.post(
            f"{BASE_URL}/api/projects/{pid}/publish",
            json={"is_public": False},
        )
        assert r.status_code == 200
        assert r.json()["is_public"] is False

        g = requests.get(f"{BASE_URL}/api/gallery")
        assert g.status_code == 200
        assert not any(item["id"] == pid for item in g.json())

        # Non-public stream returns 404
        s = requests.get(f"{BASE_URL}/api/gallery/{pid}/stream")
        assert s.status_code == 404
