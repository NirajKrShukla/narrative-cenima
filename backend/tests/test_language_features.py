"""Backend tests for iteration_3: universal narration language support.

New features under test:
- Language parameter on ingest/text, ingest/url, ingest/file endpoints
- PATCH /projects/{pid}/settings accepts arbitrary language strings (Swahili, zh, Maori, etc.)
- POST /projects/{pid}/analyze returns language_hint field; picks up project setting
- NEW: PATCH /projects/{pid}/scenes/{sid}/narration — edit text and/or translate
- POST /narration uses per-scene language override + Claude Haiku translate on the fly

We limit Claude Haiku spend to at most 2 real calls in this file (one via PATCH translate,
one via priority-override POST /narration path).
"""
import io
import os
import time
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

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

WARRIOR = "The warrior stepped into the ancient forest, sword ready, heart steady."


# ---- helpers ----------------------------------------------------------------

def _make_project(title: str = "TEST_lang") -> str:
    r = requests.post(f"{BASE_URL}/api/projects", json={"title": title})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _seed_scene(pid: str, sid: str = "scene_1", narration: str = WARRIOR,
                language: str | None = None) -> None:
    mc = MongoClient(MONGO_URL)
    try:
        scene = {
            "id": sid,
            "title": "Forest",
            "description": "A cinematic scene.",
            "image_prompt": "Cinematic still, dramatic lighting.",
            "video_prompt": "Wide cinematic shot.",
            "narration": narration,
            "image_file": None,
            "video_file": None,
            "audio_file": None,
            "final_file": None,
        }
        if language:
            scene["language"] = language
        mc[DB_NAME]["projects"].update_one(
            {"id": pid},
            {"$set": {
                "blueprint": {"title": "Seed", "visual_style": "cinematic film still"},
                "scenes": [scene],
                "status": "analyzed",
            }},
        )
    finally:
        mc.close()


def _get_project(pid: str) -> dict:
    r = requests.get(f"{BASE_URL}/api/projects/{pid}")
    assert r.status_code == 200, r.text
    return r.json()


# ---- Ingestion language param ----------------------------------------------

class TestIngestLanguageParam:
    def test_ingest_text_with_language_persists_hint(self):
        pid = _make_project("TEST_lang_text")
        long_text = ("A long enough sample text for ingestion. " * 3).strip()
        r = requests.post(
            f"{BASE_URL}/api/projects/{pid}/ingest/text",
            json={"text": long_text, "language": "Swahili"},
        )
        assert r.status_code == 200, r.text
        doc = _get_project(pid)
        assert doc["source_type"] == "text"
        assert doc["language_hint"] == "Swahili"

    def test_ingest_text_without_language_defaults_preserved(self):
        pid = _make_project("TEST_lang_text_none")
        long_text = "A long enough sample text for ingestion. " * 3
        r = requests.post(
            f"{BASE_URL}/api/projects/{pid}/ingest/text",
            json={"text": long_text.strip()},
        )
        assert r.status_code == 200, r.text
        doc = _get_project(pid)
        # Untouched default is "auto"
        assert doc["language_hint"] == "auto"

    def test_ingest_url_with_language(self):
        pid = _make_project("TEST_lang_url")
        r = requests.post(
            f"{BASE_URL}/api/projects/{pid}/ingest/url",
            json={"url": "https://en.wikipedia.org/wiki/Ramayana", "language": "hi"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        doc = _get_project(pid)
        assert doc["language_hint"] == "hi"
        assert doc["source_type"] == "url"

    def test_ingest_file_with_language_form_field(self):
        pid = _make_project("TEST_lang_file")
        payload = ("A long enough source text stored inside a plain text file. " * 3).encode()
        files = {"file": ("story.txt", io.BytesIO(payload), "text/plain")}
        data = {"language": "Yoruba"}
        r = requests.post(
            f"{BASE_URL}/api/projects/{pid}/ingest/file",
            files=files, data=data, timeout=30,
        )
        assert r.status_code == 200, r.text
        doc = _get_project(pid)
        assert doc["language_hint"] == "Yoruba"


# ---- Settings language flexibility -----------------------------------------

class TestLanguageSettings:
    @pytest.mark.parametrize("lang", ["Swahili", "Zulu", "Yoruba", "zh", "Māori"])
    def test_patch_arbitrary_language_string_accepted(self, lang):
        pid = _make_project(f"TEST_lang_settings_{lang[:5]}")
        r = requests.patch(
            f"{BASE_URL}/api/projects/{pid}/settings",
            json={"language_hint": lang},
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["updated"].get("language_hint") == lang
        doc = _get_project(pid)
        assert doc["language_hint"] == lang

    def test_empty_string_collapses_to_auto(self):
        pid = _make_project("TEST_lang_empty")
        r = requests.patch(
            f"{BASE_URL}/api/projects/{pid}/settings",
            json={"language_hint": ""},
        )
        assert r.status_code == 200, r.text
        doc = _get_project(pid)
        assert doc["language_hint"] == "auto"

    def test_invalid_voice_still_rejected(self):
        pid = _make_project("TEST_lang_settings_voice")
        r = requests.patch(
            f"{BASE_URL}/api/projects/{pid}/settings",
            json={"voice": "not_a_voice"},
        )
        assert r.status_code == 400


# ---- Analyze uses project language_hint ------------------------------------

class TestAnalyzeUsesProjectLanguage:
    def test_analyze_returns_language_hint_from_project(self):
        """Analyze should return `language_hint` = project's language_hint when body omits it.

        We do NOT wait for full analysis (kept short/cheap); we just verify the
        immediate response contains the expected language_hint.
        """
        pid = _make_project("TEST_analyze_lang")
        long_text = "A cinematic short story about heroes and trials. " * 6
        # Ingest w/ language "Spanish"
        r = requests.post(
            f"{BASE_URL}/api/projects/{pid}/ingest/text",
            json={"text": long_text.strip(), "language": "Spanish"},
        )
        assert r.status_code == 200
        # Analyze WITHOUT language_hint in body
        r2 = requests.post(f"{BASE_URL}/api/projects/{pid}/analyze", json={}, timeout=15)
        assert r2.status_code == 200, r2.text
        data = r2.json()
        assert data["ok"] is True
        assert data["status"] == "analyzing"
        assert data.get("language_hint") == "Spanish", data

    def test_analyze_body_overrides_project(self):
        pid = _make_project("TEST_analyze_lang_override")
        long_text = "A cinematic short story about heroes and trials. " * 6
        requests.post(
            f"{BASE_URL}/api/projects/{pid}/ingest/text",
            json={"text": long_text.strip(), "language": "Spanish"},
        )
        r = requests.post(
            f"{BASE_URL}/api/projects/{pid}/analyze",
            json={"language_hint": "French"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        assert r.json().get("language_hint") == "French"


# ---- PATCH scene narration (edit + translate) ------------------------------

class TestSceneNarrationEdit:
    def test_edit_direct_narration_text(self):
        pid = _make_project("TEST_edit_narr")
        _seed_scene(pid, "scene_1", WARRIOR)
        # Pre-populate audio_file to prove it gets cleared
        MongoClient(MONGO_URL)[DB_NAME]["projects"].update_one(
            {"id": pid, "scenes.id": "scene_1"},
            {"$set": {"scenes.$.audio_file": "stale.mp3", "scenes.$.final_file": "stale_final.mp4"}},
        )

        new_text = "A completely new sentence."
        r = requests.patch(
            f"{BASE_URL}/api/projects/{pid}/scenes/scene_1/narration",
            json={"narration": new_text, "language": "en"},
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] is True
        assert d["narration"] == new_text
        assert d["language"] == "en"

        doc = _get_project(pid)
        scene = doc["scenes"][0]
        assert scene["narration"] == new_text
        assert scene.get("language") == "en"
        # Old audio/final cleared
        assert scene.get("audio_file") is None
        assert scene.get("final_file") is None

    def test_translate_via_language_only(self):
        """CLAUDE HAIKU CALL #1 — translate WARRIOR into Hindi."""
        pid = _make_project("TEST_translate_hi")
        _seed_scene(pid, "scene_1", WARRIOR)
        r = requests.patch(
            f"{BASE_URL}/api/projects/{pid}/scenes/scene_1/narration",
            json={"language": "Hindi"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] is True
        assert d["language"] == "Hindi"
        assert d["narration"] and isinstance(d["narration"], str)
        # Non-empty translation and not the same as source
        assert len(d["narration"]) > 0
        # Devanagari script check — must contain at least one non-ASCII char
        has_non_ascii = any(ord(c) > 127 for c in d["narration"])
        assert has_non_ascii, f"Expected native (Devanagari) script, got: {d['narration']!r}"

        # Persistence
        doc = _get_project(pid)
        scene = doc["scenes"][0]
        assert scene["narration"] == d["narration"]
        assert scene.get("language") == "Hindi"

    def test_empty_body_returns_400(self):
        pid = _make_project("TEST_edit_empty")
        _seed_scene(pid)
        r = requests.patch(
            f"{BASE_URL}/api/projects/{pid}/scenes/scene_1/narration",
            json={},
        )
        assert r.status_code == 400, r.text
        assert "narration" in r.text.lower() or "language" in r.text.lower()

    def test_invalid_scene_returns_404(self):
        pid = _make_project("TEST_edit_bad_scene")
        _seed_scene(pid)
        r = requests.patch(
            f"{BASE_URL}/api/projects/{pid}/scenes/no_such_scene/narration",
            json={"narration": "hi"},
        )
        assert r.status_code == 404

    def test_invalid_project_returns_404(self):
        r = requests.patch(
            f"{BASE_URL}/api/projects/no_such_pid/scenes/scene_1/narration",
            json={"narration": "hi"},
        )
        assert r.status_code == 404


# ---- POST /narration honours per-scene language & priority order -----------

class TestNarrationLanguagePriority:
    def test_narration_translates_when_language_differs(self):
        """CLAUDE HAIKU CALL #2 — narration endpoint should translate on the fly.

        Priority: body.language > scene.language > project.language_hint.
        We pre-store scene.language='Hindi' with English narration.
        Then call POST /narration with body language='Spanish' — should translate to Spanish,
        persist, and generate an mp3.
        """
        pid = _make_project("TEST_narr_priority")
        _seed_scene(pid, "scene_1", WARRIOR, language="Hindi")

        r = requests.post(
            f"{BASE_URL}/api/projects/{pid}/scenes/scene_1/narration",
            json={"language": "Spanish"},
            timeout=120,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] is True
        assert d["audio_file"].endswith(".mp3")
        assert d.get("language") == "Spanish"

        # Verify persistence — scene.language now Spanish, narration changed
        doc = _get_project(pid)
        scene = doc["scenes"][0]
        assert scene.get("language") == "Spanish"
        assert scene["narration"] != WARRIOR  # translated
        assert scene.get("audio_file", "").endswith(".mp3")

        # Storage fetch works
        af = d["audio_file"]
        r2 = requests.get(f"{BASE_URL}/api/storage/{af}", timeout=60)
        assert r2.status_code == 200
        assert r2.headers.get("content-type", "").startswith("audio/mpeg")
        assert len(r2.content) > 500


# ---- Translate helper resilience (no real call — use ai_services directly) --

class TestTranslateHelperResilience:
    def test_translate_returns_original_on_empty_target(self):
        """Guard clause: no target language -> returns original untouched (no LLM call)."""
        import asyncio
        import ai_services  # backend module
        out = asyncio.get_event_loop().run_until_complete(
            ai_services.translate_narration(WARRIOR, "")
        )
        assert out == WARRIOR

    def test_translate_returns_original_on_auto(self):
        import asyncio
        import ai_services
        out = asyncio.get_event_loop().run_until_complete(
            ai_services.translate_narration(WARRIOR, "auto")
        )
        assert out == WARRIOR

    def test_translate_returns_original_on_empty_text(self):
        import asyncio
        import ai_services
        out = asyncio.get_event_loop().run_until_complete(
            ai_services.translate_narration("", "Hindi")
        )
        assert out == ""
