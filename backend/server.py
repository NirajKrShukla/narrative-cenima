"""Story-to-Film AI Agent — FastAPI backend."""
from __future__ import annotations
import os
import re
import json
import uuid
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Any

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi import Request
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient

import ingestion
import ai_services
import assembly
import payments

STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "/app/backend/storage"))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("story2film")

# --- DB setup ---
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
projects_col = db["projects"]
payments_col = db["payment_transactions"]
users_col = db["users"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Models ---
class ProjectCreate(BaseModel):
    title: str = Field(default="Untitled Film")


class UrlIngest(BaseModel):
    url: str
    language: Optional[str] = None


class TextIngest(BaseModel):
    text: str
    language: Optional[str] = None


class AnalyzeRequest(BaseModel):
    language_hint: Optional[str] = None


class GenerateVideoRequest(BaseModel):
    duration: int = 4  # 4, 8, or 12
    size: str = "1280x720"
    model: str = "sora-2"


class GenerateNarrationRequest(BaseModel):
    voice: Optional[str] = None
    model: Optional[str] = None
    language: Optional[str] = None       # override for this scene


class SceneNarrationEdit(BaseModel):
    narration: Optional[str] = None      # replace narration text directly
    language: Optional[str] = None       # if provided (and narration not), translate existing narration to this language
    voice: Optional[str] = None          # per-scene voice override
    voice_model: Optional[str] = None    # per-scene voice model override


class VoicePreviewRequest(BaseModel):
    voice: str = "onyx"
    model: str = "tts-1"
    language: Optional[str] = None       # optional language for the sample text


class ProjectSettings(BaseModel):
    voice: Optional[str] = None
    voice_model: Optional[str] = None
    language_hint: Optional[str] = None
    title: Optional[str] = None


class BatchRequest(BaseModel):
    mode: str = "all"          # "images" | "narration" | "kenburns" | "sora" | "all"
    video_type: str = "kenburns"  # used when mode=="all" or "videos" — "kenburns" or "sora"
    duration: int = 4
    size: str = "1280x720"


class DubRequest(BaseModel):
    languages: list[str] = Field(default_factory=list)   # e.g. ["hi", "es", "Yoruba"]
    voice: Optional[str] = None    # optional voice override for all dubs


class PublishRequest(BaseModel):
    is_public: bool = True
    tip_vpa: Optional[str] = None


class TipRequest(BaseModel):
    amount_inr: float
    origin_url: str
    user_id: str
    message: Optional[str] = None


class CheckoutRequest(BaseModel):
    origin_url: str
    user_id: str


# --- App ---
app = FastAPI(title="Story-to-Film AI Agent")

api = APIRouter(prefix="/api")


def project_public(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


@api.get("/health")
async def health():
    return {"status": "ok", "time": now_iso()}


@api.post("/projects")
async def create_project(body: ProjectCreate):
    pid = uuid.uuid4().hex[:12]
    doc = {
        "id": pid,
        "title": body.title or "Untitled Film",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "source_text": "",
        "source_type": None,
        "source_meta": {},
        "blueprint": None,        # analyzed JSON
        "characters": [],         # {..., image_file}
        "scenes": [],             # {..., image_file, video_file, audio_file, final_file}
        "final_film": None,
        "final_srt": None,       # SRT file for the final film
        "dubs": [],              # [{language, film_file, srt_file, size_bytes, created_at}]
        "dub_job": None,         # {running, total, completed, current, errors[]}
        "status": "created",
        "paid": False,
        "free_granted": False,
        "unlocked_at": None,
        "price_inr": None,
        # Voice / language settings (project-level defaults)
        "voice": "onyx",
        "voice_model": "tts-1",
        "language_hint": "auto",
        # Batch job state (for progress UI)
        "batch": None,   # {job_id, mode, total, completed, current, running, started_at, finished_at, errors:[]}
        # Public gallery
        "is_public": False,
        "tip_vpa": None,      # optional display-only UPI VPA
        "views": 0,
        "tips_total_inr": 0.0,
    }
    await projects_col.insert_one(doc)
    return project_public(doc)


@api.get("/projects")
async def list_projects():
    docs = await projects_col.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    # Return light list
    light = []
    for d in docs:
        light.append({
            "id": d["id"],
            "title": d.get("title"),
            "created_at": d.get("created_at"),
            "status": d.get("status"),
            "scene_count": len(d.get("scenes") or []),
            "has_final": bool(d.get("final_film")),
        })
    return light


@api.get("/projects/{pid}")
async def get_project(pid: str):
    doc = await projects_col.find_one({"id": pid}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Project not found")
    return doc


@api.delete("/projects/{pid}")
async def delete_project(pid: str):
    res = await projects_col.delete_one({"id": pid})
    if res.deleted_count == 0:
        raise HTTPException(404, "Project not found")
    return {"deleted": True}


async def _update_source(pid: str, text: str, source_type: str, meta: dict | None = None, language: str | None = None):
    if not text or len(text.strip()) < 30:
        raise HTTPException(400, "Extracted text is too short — please provide a richer source.")
    update = {
        "source_text": text[:40000],
        "source_type": source_type,
        "source_meta": meta or {},
        "status": "ingested",
        "updated_at": now_iso(),
    }
    if language:
        update["language_hint"] = language.strip()[:60]
    await projects_col.update_one({"id": pid}, {"$set": update})


@api.post("/projects/{pid}/ingest/text")
async def ingest_text(pid: str, body: TextIngest):
    doc = await projects_col.find_one({"id": pid})
    if not doc:
        raise HTTPException(404, "Project not found")
    await _update_source(pid, body.text, "text", language=body.language)
    return {"ok": True, "chars": len(body.text)}


@api.post("/projects/{pid}/ingest/url")
async def ingest_url(pid: str, body: UrlIngest):
    doc = await projects_col.find_one({"id": pid})
    if not doc:
        raise HTTPException(404, "Project not found")
    try:
        text = await ingestion.extract_from_url(body.url)
    except Exception as e:
        raise HTTPException(400, f"Failed to fetch URL: {e}")
    await _update_source(pid, text, "url", {"url": body.url}, language=body.language)
    return {"ok": True, "chars": len(text)}


@api.post("/projects/{pid}/ingest/file")
async def ingest_file(pid: str, file: UploadFile = File(...), language: Optional[str] = Form(None)):
    doc = await projects_col.find_one({"id": pid})
    if not doc:
        raise HTTPException(404, "Project not found")
    data = await file.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, "File too large (max 15 MB)")
    try:
        text = await ingestion.extract_from_upload(file.filename or "", data)
    except Exception as e:
        raise HTTPException(400, f"Could not parse file: {e}")
    await _update_source(pid, text, "file", {"filename": file.filename}, language=language)
    return {"ok": True, "chars": len(text), "filename": file.filename}


@api.post("/projects/{pid}/ingest/voice")
async def ingest_voice(pid: str, file: UploadFile = File(...), language: Optional[str] = Form(None)):
    doc = await projects_col.find_one({"id": pid})
    if not doc:
        raise HTTPException(404, "Project not found")
    tmp = STORAGE_DIR / f"voice_{pid}_{uuid.uuid4().hex[:6]}_{file.filename}"
    tmp.write_bytes(await file.read())
    # Whisper accepts 2-letter ISO 639-1 codes only. Extract from any full name -> code map.
    whisper_lang = ingestion.iso_code_for_language(language) if language else None
    try:
        text = await ingestion.transcribe_audio(str(tmp), language=whisper_lang)
    except Exception as e:
        raise HTTPException(400, f"Transcription failed: {e}")
    finally:
        try:
            tmp.unlink()
        except Exception:
            pass
    await _update_source(pid, text, "voice", {"filename": file.filename, "language": language}, language=language)
    return {"ok": True, "chars": len(text), "transcript": text[:500]}


async def _analyze_task(pid: str, source_text: str, language_hint: str):
    try:
        blueprint = await ai_services.analyze_story(source_text, language_hint or "auto")
    except Exception as e:
        logger.error(f"Analyze failed for {pid}: {e}")
        await projects_col.update_one(
            {"id": pid},
            {"$set": {"status": "error", "last_error": str(e)[:400], "updated_at": now_iso()}},
        )
        return

    characters = blueprint.get("characters") or []
    scenes = blueprint.get("scenes") or []
    # Ensure every character has a unique TTS voice (repair if LLM missed any)
    narrator_voice = blueprint.get("narrator_voice") or "fable"
    characters, narrator_voice = ai_services.assign_unique_voices(characters, narrator_voice)
    blueprint["narrator_voice"] = narrator_voice
    for i, c in enumerate(characters):
        c["id"] = c.get("id") or f"char_{i+1}"
        c["image_file"] = None
    for i, s in enumerate(scenes):
        s["id"] = s.get("id") or f"scene_{i+1}"
        s["image_file"] = None
        s["video_file"] = None
        s["audio_file"] = None
        s["final_file"] = None
        # Ensure dialogue_lines is a list (may be missing on older blueprints)
        if not isinstance(s.get("dialogue_lines"), list):
            s["dialogue_lines"] = []

    await projects_col.update_one(
        {"id": pid},
        {"$set": {
            "blueprint": blueprint,
            "title": blueprint.get("title") or "Untitled Film",
            "characters": characters,
            "scenes": scenes,
            "status": "analyzed",
            "last_error": None,
            "updated_at": now_iso(),
        }},
    )


@api.post("/projects/{pid}/analyze")
async def analyze(pid: str, body: AnalyzeRequest = AnalyzeRequest()):
    """Kick off analysis as a background task and return immediately.
    Frontend polls GET /projects/{pid} until status == 'analyzed' or 'error'.
    This avoids Cloudflare's ~100s idle-timeout on long Claude calls."""
    doc = await projects_col.find_one({"id": pid})
    if not doc:
        raise HTTPException(404, "Project not found")
    if not doc.get("source_text"):
        raise HTTPException(400, "No source text ingested yet")
    if doc.get("status") == "analyzing":
        return {"ok": True, "status": "analyzing", "already_running": True}

    await projects_col.update_one({"id": pid}, {"$set": {"status": "analyzing", "last_error": None}})
    # Priority: request body > project setting > auto
    lang = body.language_hint or doc.get("language_hint") or "auto"
    asyncio.create_task(_analyze_task(pid, doc["source_text"], lang))
    return {"ok": True, "status": "analyzing", "language_hint": lang}


@api.post("/projects/{pid}/characters/{cid}/image")
async def gen_character_image(pid: str, cid: str):
    doc = await projects_col.find_one({"id": pid})
    if not doc:
        raise HTTPException(404, "Project not found")
    char = next((c for c in doc.get("characters") or [] if c.get("id") == cid), None)
    if not char:
        raise HTTPException(404, "Character not found")

    visual_style = (doc.get("blueprint") or {}).get("visual_style") or "cinematic film still"
    prompt = (
        f"Character portrait, cinematic, {visual_style}. "
        f"ORIGINAL character design — {char.get('name')}, {char.get('archetype')}. "
        f"{char.get('description')} Full body or three-quarter shot on dramatic backdrop. "
        f"Period-authentic historical/archaeological references only. "
        f"Do NOT resemble any specific film, TV show, comic, game, or real actor. "
        f"No text, no logos, no watermarks."
    )
    fname = f"{pid}_char_{cid}.png"
    try:
        await ai_services.generate_image(prompt, fname)
    except Exception as e:
        raise HTTPException(500, f"Character image generation failed: {e}")
    await projects_col.update_one(
        {"id": pid, "characters.id": cid},
        {"$set": {"characters.$.image_file": fname, "updated_at": now_iso()}},
    )
    return {"ok": True, "image_file": fname}


@api.post("/projects/{pid}/scenes/{sid}/image")
async def gen_scene_image(pid: str, sid: str):
    doc = await projects_col.find_one({"id": pid})
    if not doc:
        raise HTTPException(404, "Project not found")
    scene = next((s for s in doc.get("scenes") or [] if s.get("id") == sid), None)
    if not scene:
        raise HTTPException(404, "Scene not found")

    visual_style = (doc.get("blueprint") or {}).get("visual_style") or "cinematic film still"
    prompt = f"{scene.get('image_prompt') or scene.get('description')}. Style: {visual_style}. No watermark, no text."
    fname = f"{pid}_scene_{sid}.png"
    try:
        await ai_services.generate_image(prompt, fname)
    except Exception as e:
        raise HTTPException(500, f"Scene image generation failed: {e}")
    await projects_col.update_one(
        {"id": pid, "scenes.id": sid},
        {"$set": {"scenes.$.image_file": fname, "updated_at": now_iso()}},
    )
    return {"ok": True, "image_file": fname}


@api.post("/projects/{pid}/scenes/{sid}/video")
async def gen_scene_video(pid: str, sid: str, body: GenerateVideoRequest = GenerateVideoRequest()):
    doc = await projects_col.find_one({"id": pid})
    if not doc:
        raise HTTPException(404, "Project not found")
    scene = next((s for s in doc.get("scenes") or [] if s.get("id") == sid), None)
    if not scene:
        raise HTTPException(404, "Scene not found")

    visual_style = (doc.get("blueprint") or {}).get("visual_style") or "cinematic 35mm"
    prompt = f"{scene.get('video_prompt') or scene.get('description')}. Cinematic style: {visual_style}. No text or watermark."
    fname = f"{pid}_scene_{sid}.mp4"

    if body.duration not in (4, 8, 12):
        raise HTTPException(400, "duration must be 4, 8, or 12")
    if body.size not in ("1280x720", "1792x1024", "1024x1792", "1024x1024"):
        raise HTTPException(400, "invalid size")

    try:
        await asyncio.to_thread(
            ai_services.generate_video_sync,
            prompt, fname, body.size, body.duration, body.model,
        )
    except Exception as e:
        raise HTTPException(500, f"Sora 2 video generation failed: {e}")

    await projects_col.update_one(
        {"id": pid, "scenes.id": sid},
        {"$set": {"scenes.$.video_file": fname, "updated_at": now_iso()}},
    )
    return {"ok": True, "video_file": fname}


@api.post("/projects/{pid}/scenes/{sid}/kenburns")
async def gen_scene_kenburns(pid: str, sid: str):
    """Fallback: create a video from the scene image using Ken-Burns pan/zoom."""
    doc = await projects_col.find_one({"id": pid})
    if not doc:
        raise HTTPException(404, "Project not found")
    scene = next((s for s in doc.get("scenes") or [] if s.get("id") == sid), None)
    if not scene:
        raise HTTPException(404, "Scene not found")
    if not scene.get("image_file"):
        raise HTTPException(400, "Generate the scene image first")
    fname = f"{pid}_scene_{sid}_kb.mp4"
    try:
        await asyncio.to_thread(assembly.image_to_video, scene["image_file"], fname, 6, "1280x720")
    except Exception as e:
        raise HTTPException(500, f"Ken-Burns failed: {e}")
    await projects_col.update_one(
        {"id": pid, "scenes.id": sid},
        {"$set": {"scenes.$.video_file": fname, "updated_at": now_iso()}},
    )
    return {"ok": True, "video_file": fname}


@api.post("/projects/{pid}/scenes/{sid}/narration")
async def gen_scene_narration(pid: str, sid: str, body: GenerateNarrationRequest = GenerateNarrationRequest()):
    doc = await projects_col.find_one({"id": pid})
    if not doc:
        raise HTTPException(404, "Project not found")
    scene = next((s for s in doc.get("scenes") or [] if s.get("id") == sid), None)
    if not scene:
        raise HTTPException(404, "Scene not found")

    original_text = scene.get("narration") or scene.get("description") or ""
    # Determine target language: request > scene override > project default
    target_lang = (body.language or scene.get("language") or doc.get("language_hint") or "").strip()

    text = original_text
    # If a language is requested and current narration wasn't already in it, translate.
    if target_lang and target_lang.lower() not in ("auto", ""):
        # Only translate if the scene's stored language differs from the target
        if (scene.get("language") or "").lower() != target_lang.lower():
            try:
                translated = await ai_services.translate_narration(original_text, target_lang)
                if translated and translated != original_text:
                    text = translated
                    # Persist translated narration + language on the scene for reuse
                    await projects_col.update_one(
                        {"id": pid, "scenes.id": sid},
                        {"$set": {
                            "scenes.$.narration": translated,
                            "scenes.$.language": target_lang,
                        }},
                    )
            except Exception as e:
                logger.error(f"Translation failed, using original: {e}")

    fname = f"{pid}_scene_{sid}.mp3"
    voice = body.voice or scene.get("voice") or doc.get("voice") or "onyx"
    model = body.model or scene.get("voice_model") or doc.get("voice_model") or "tts-1"

    # ---- Multi-voice per character ----
    # If the scene has dialogue_lines with a speaker breakdown, generate audio per line
    # in each speaker's own voice, then concat. This is the default new behavior.
    dialogue_lines = scene.get("dialogue_lines") or []
    characters = doc.get("characters") or []
    narrator_voice = (
        (doc.get("blueprint") or {}).get("narrator_voice")
        or doc.get("voice")
        or "fable"
    )
    used_multivoice = False
    if isinstance(dialogue_lines, list) and any((ln or {}).get("text") for ln in dialogue_lines):
        # If a language override was applied, translate each line into the target language
        if target_lang and target_lang.lower() not in ("auto", ""):
            translated_lines = []
            for ln in dialogue_lines:
                t = (ln.get("text") or "").strip()
                if not t:
                    continue
                try:
                    tr = await ai_services.translate_narration(t, target_lang)
                    translated_lines.append({"speaker": ln.get("speaker") or "narrator", "text": tr or t})
                except Exception:
                    translated_lines.append({"speaker": ln.get("speaker") or "narrator", "text": t})
            dialogue_lines = translated_lines
        try:
            await ai_services.generate_scene_audio_multivoice(
                dialogue_lines, characters, narrator_voice, fname, model=model,
            )
            used_multivoice = True
        except Exception as e:
            logger.error(f"Multi-voice audio failed, falling back to single voice: {e}")

    if not used_multivoice:
        try:
            await ai_services.generate_narration(text, fname, voice=voice, model=model)
        except Exception as e:
            raise HTTPException(500, f"TTS failed: {e}")
    await projects_col.update_one(
        {"id": pid, "scenes.id": sid},
        {"$set": {"scenes.$.audio_file": fname, "updated_at": now_iso()}},
    )
    return {"ok": True, "audio_file": fname, "language": target_lang or None, "voice": voice, "voice_model": model}


@api.patch("/projects/{pid}/scenes/{sid}/narration")
async def edit_scene_narration(pid: str, sid: str, body: SceneNarrationEdit):
    """Edit narration text directly, or translate the existing narration into a target language."""
    doc = await projects_col.find_one({"id": pid})
    if not doc:
        raise HTTPException(404, "Project not found")
    scene = next((s for s in doc.get("scenes") or [] if s.get("id") == sid), None)
    if not scene:
        raise HTTPException(404, "Scene not found")

    new_text = None
    new_lang = None
    voice_update = None
    voice_model_update = None

    # Voice/model overrides can be set independently
    ALLOWED_VOICES = {"alloy", "ash", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer"}
    if body.voice is not None:
        if body.voice == "" or body.voice.lower() == "default":
            voice_update = None  # clear override
        elif body.voice not in ALLOWED_VOICES:
            raise HTTPException(400, f"voice must be one of {sorted(ALLOWED_VOICES)} or empty to clear")
        else:
            voice_update = body.voice
    if body.voice_model is not None:
        if body.voice_model == "" or body.voice_model.lower() == "default":
            voice_model_update = None
        elif body.voice_model not in {"tts-1", "tts-1-hd"}:
            raise HTTPException(400, "voice_model must be tts-1 or tts-1-hd")
        else:
            voice_model_update = body.voice_model

    if body.narration is not None:
        new_text = body.narration.strip()[:2000]
        new_lang = body.language.strip()[:60] if body.language else scene.get("language")
    elif body.language:
        # Translate the current narration into the requested language
        current = scene.get("narration") or scene.get("description") or ""
        try:
            translated = await ai_services.translate_narration(current, body.language)
        except Exception as e:
            raise HTTPException(500, f"Translation failed: {e}")
        new_text = translated
        new_lang = body.language.strip()[:60]
    elif body.voice is None and body.voice_model is None:
        raise HTTPException(400, "Provide `narration` (to set text), `language` (to translate), or `voice`/`voice_model` to update")

    updates = {"updated_at": now_iso()}
    if new_text is not None:
        updates["scenes.$.narration"] = new_text
        # Clear stale audio when text changes
        updates["scenes.$.audio_file"] = None
        updates["scenes.$.final_file"] = None
    if new_lang is not None:
        updates["scenes.$.language"] = new_lang
    if body.voice is not None:
        updates["scenes.$.voice"] = voice_update
    if body.voice_model is not None:
        updates["scenes.$.voice_model"] = voice_model_update

    await projects_col.update_one({"id": pid, "scenes.id": sid}, {"$set": updates})
    return {
        "ok": True,
        "narration": new_text if new_text is not None else scene.get("narration"),
        "language": new_lang if new_lang is not None else scene.get("language"),
        "voice": voice_update if body.voice is not None else scene.get("voice"),
        "voice_model": voice_model_update if body.voice_model is not None else scene.get("voice_model"),
    }


@api.post("/projects/{pid}/scenes/{sid}/mux")
async def mux_scene_endpoint(pid: str, sid: str):
    """Mux the scene video + audio + subtitle overlay to produce final scene clip."""
    doc = await projects_col.find_one({"id": pid})
    if not doc:
        raise HTTPException(404, "Project not found")
    scene = next((s for s in doc.get("scenes") or [] if s.get("id") == sid), None)
    if not scene:
        raise HTTPException(404, "Scene not found")
    if not scene.get("video_file"):
        raise HTTPException(400, "Scene has no video yet")
    fname = f"{pid}_scene_{sid}_final.mp4"
    try:
        await asyncio.to_thread(
            assembly.mux_scene,
            scene["video_file"], scene.get("audio_file"), fname, scene.get("narration"),
        )
    except Exception as e:
        raise HTTPException(500, f"Mux failed: {e}")
    await projects_col.update_one(
        {"id": pid, "scenes.id": sid},
        {"$set": {"scenes.$.final_file": fname, "updated_at": now_iso()}},
    )
    return {"ok": True, "final_file": fname}


@api.post("/projects/{pid}/assemble")
async def assemble_film(pid: str):
    doc = await projects_col.find_one({"id": pid})
    if not doc:
        raise HTTPException(404, "Project not found")
    scenes = doc.get("scenes") or []
    # Use each scene's final_file if present, else video_file. Also collect narrations.
    ordered_files = []
    ordered_narr = []
    for s in scenes:
        f = s.get("final_file") or s.get("video_file")
        if f:
            ordered_files.append(f)
            ordered_narr.append(s.get("narration") or "")
    if not ordered_files:
        raise HTTPException(400, "No scene videos to assemble")

    fname = f"{pid}_final_film.mp4"
    srt_name = f"{pid}_final_film.srt"
    try:
        await asyncio.to_thread(
            assembly.concat_with_subs,
            ordered_files, ordered_narr, fname, srt_name,
        )
    except Exception as e:
        raise HTTPException(500, f"Assembly failed: {e}")
    await projects_col.update_one(
        {"id": pid},
        {"$set": {
            "final_film": fname,
            "final_srt": srt_name,
            "status": "assembled",
            "updated_at": now_iso(),
        }},
    )
    return {"ok": True, "final_film": fname, "final_srt": srt_name}


# ----------------------------------------------------------------------------
# Project settings (voice, language, title)
# ----------------------------------------------------------------------------
@api.patch("/projects/{pid}/settings")
async def update_settings(pid: str, body: ProjectSettings):
    doc = await projects_col.find_one({"id": pid})
    if not doc:
        raise HTTPException(404, "Project not found")
    updates = {}
    if body.voice is not None:
        allowed = {"alloy", "ash", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer"}
        if body.voice not in allowed:
            raise HTTPException(400, f"Voice must be one of {sorted(allowed)}")
        updates["voice"] = body.voice
    if body.voice_model is not None:
        if body.voice_model not in {"tts-1", "tts-1-hd"}:
            raise HTTPException(400, "voice_model must be tts-1 or tts-1-hd")
        updates["voice_model"] = body.voice_model
    if body.language_hint is not None:
        # Accept any language name or ISO code — TTS and Claude both understand them.
        updates["language_hint"] = body.language_hint.strip()[:60] or "auto"
    if body.title is not None:
        updates["title"] = body.title.strip()[:120] or "Untitled Film"
    if not updates:
        return {"ok": True, "updated": {}}
    updates["updated_at"] = now_iso()
    await projects_col.update_one({"id": pid}, {"$set": updates})
    return {"ok": True, "updated": updates}


# ----------------------------------------------------------------------------
# Batch generation with progress
# ----------------------------------------------------------------------------

async def _bump_batch(pid: str, **kv):
    """Update project.batch fields, keeping the same job."""
    updates = {f"batch.{k}": v for k, v in kv.items()}
    updates["updated_at"] = now_iso()
    await projects_col.update_one({"id": pid}, {"$set": updates})


async def _batch_worker(pid: str, mode: str, video_type: str, duration: int, size: str):
    """Background worker that processes scenes sequentially, updating progress."""
    doc = await projects_col.find_one({"id": pid})
    if not doc:
        return
    scenes = doc.get("scenes") or []

    # Determine steps per scene
    steps = []
    if mode in ("all", "images"):
        steps.append("image")
    if mode in ("all", "narration"):
        steps.append("narration")
    if mode in ("all", "sora", "kenburns"):
        steps.append("video")
    if mode == "all":
        steps.append("mux")

    total = len(scenes) * len(steps)
    completed = 0
    errors: list[str] = []

    await _bump_batch(pid, total=total, completed=0, current="starting", running=True, errors=[])

    for scene in scenes:
        sid = scene.get("id")
        for step in steps:
            await _bump_batch(pid, current=f"{sid}:{step}")
            try:
                if step == "image":
                    visual_style = (doc.get("blueprint") or {}).get("visual_style") or "cinematic film still"
                    prompt = f"{scene.get('image_prompt') or scene.get('description')}. Style: {visual_style}. No watermark, no text."
                    fname = f"{pid}_scene_{sid}.png"
                    await ai_services.generate_image(prompt, fname)
                    await projects_col.update_one(
                        {"id": pid, "scenes.id": sid},
                        {"$set": {"scenes.$.image_file": fname}},
                    )
                elif step == "narration":
                    text = scene.get("narration") or scene.get("description") or ""
                    fname = f"{pid}_scene_{sid}.mp3"
                    voice = doc.get("voice") or "onyx"
                    v_model = doc.get("voice_model") or "tts-1"
                    dialogue_lines = scene.get("dialogue_lines") or []
                    characters = doc.get("characters") or []
                    narrator_voice = (
                        (doc.get("blueprint") or {}).get("narrator_voice")
                        or voice
                        or "fable"
                    )
                    if isinstance(dialogue_lines, list) and any((ln or {}).get("text") for ln in dialogue_lines):
                        try:
                            await ai_services.generate_scene_audio_multivoice(
                                dialogue_lines, characters, narrator_voice, fname, model=v_model,
                            )
                        except Exception as e:
                            logger.error(f"Batch multi-voice failed for {sid}, falling back: {e}")
                            await ai_services.generate_narration(text, fname, voice=voice, model=v_model)
                    else:
                        await ai_services.generate_narration(text, fname, voice=voice, model=v_model)
                    await projects_col.update_one(
                        {"id": pid, "scenes.id": sid},
                        {"$set": {"scenes.$.audio_file": fname}},
                    )
                elif step == "video":
                    # Refresh scene to get image_file if updated
                    fresh = await projects_col.find_one({"id": pid, "scenes.id": sid}, {"scenes.$": 1})
                    fresh_scene = (fresh.get("scenes") or [scene])[0] if fresh else scene
                    fname_v = f"{pid}_scene_{sid}.mp4"
                    kb_source = video_type if mode not in ("sora", "kenburns") else mode
                    if kb_source == "sora":
                        visual_style = (doc.get("blueprint") or {}).get("visual_style") or "cinematic 35mm"
                        prompt = f"{scene.get('video_prompt') or scene.get('description')}. Cinematic style: {visual_style}."
                        await asyncio.to_thread(
                            ai_services.generate_video_sync,
                            prompt, fname_v, size, duration, "sora-2",
                        )
                    else:
                        # Ken-Burns needs an image
                        if not fresh_scene.get("image_file"):
                            raise RuntimeError("Image required for Ken-Burns (run 'images' first)")
                        fname_v = f"{pid}_scene_{sid}_kb.mp4"
                        await asyncio.to_thread(
                            assembly.image_to_video, fresh_scene["image_file"], fname_v, 6, "1280x720",
                        )
                    await projects_col.update_one(
                        {"id": pid, "scenes.id": sid},
                        {"$set": {"scenes.$.video_file": fname_v}},
                    )
                elif step == "mux":
                    fresh = await projects_col.find_one({"id": pid, "scenes.id": sid}, {"scenes.$": 1})
                    fresh_scene = (fresh.get("scenes") or [scene])[0] if fresh else scene
                    if fresh_scene.get("video_file"):
                        fname_f = f"{pid}_scene_{sid}_final.mp4"
                        await asyncio.to_thread(
                            assembly.mux_scene,
                            fresh_scene["video_file"], fresh_scene.get("audio_file"), fname_f, fresh_scene.get("narration"),
                        )
                        await projects_col.update_one(
                            {"id": pid, "scenes.id": sid},
                            {"$set": {"scenes.$.final_file": fname_f}},
                        )
            except Exception as e:
                errors.append(f"{sid}:{step}: {str(e)[:200]}")
                logger.error(f"Batch error {sid}:{step} — {e}")
            completed += 1
            await _bump_batch(pid, completed=completed, errors=errors)

    # If mode==all, auto-assemble
    if mode == "all":
        try:
            await _bump_batch(pid, current="assembling")
            fresh = await projects_col.find_one({"id": pid})
            scenes_final = fresh.get("scenes") or []
            ordered_files = []
            ordered_narr = []
            for s in scenes_final:
                f = s.get("final_file") or s.get("video_file")
                if f:
                    ordered_files.append(f)
                    ordered_narr.append(s.get("narration") or "")
            if ordered_files:
                fname_final = f"{pid}_final_film.mp4"
                srt_final = f"{pid}_final_film.srt"
                await asyncio.to_thread(
                    assembly.concat_with_subs, ordered_files, ordered_narr, fname_final, srt_final,
                )
                await projects_col.update_one(
                    {"id": pid},
                    {"$set": {"final_film": fname_final, "final_srt": srt_final, "status": "assembled"}},
                )
        except Exception as e:
            errors.append(f"assemble: {str(e)[:200]}")

    await _bump_batch(
        pid,
        running=False,
        current="done",
        finished_at=now_iso(),
        errors=errors,
    )


@api.post("/projects/{pid}/batch")
async def start_batch(pid: str, body: BatchRequest):
    doc = await projects_col.find_one({"id": pid})
    if not doc:
        raise HTTPException(404, "Project not found")
    if not (doc.get("scenes") or []):
        raise HTTPException(400, "Analyze the story first to produce scenes")
    if (doc.get("batch") or {}).get("running"):
        return {"ok": True, "already_running": True}
    if body.mode not in ("all", "images", "narration", "sora", "kenburns"):
        raise HTTPException(400, "mode must be one of: all, images, narration, sora, kenburns")
    if body.video_type not in ("kenburns", "sora"):
        raise HTTPException(400, "video_type must be kenburns or sora")

    job_id = uuid.uuid4().hex[:10]
    await projects_col.update_one(
        {"id": pid},
        {"$set": {"batch": {
            "job_id": job_id,
            "mode": body.mode,
            "video_type": body.video_type,
            "duration": body.duration,
            "size": body.size,
            "total": 0,
            "completed": 0,
            "current": "queued",
            "running": True,
            "started_at": now_iso(),
            "finished_at": None,
            "errors": [],
        }}},
    )
    asyncio.create_task(_batch_worker(pid, body.mode, body.video_type, body.duration, body.size))
    return {"ok": True, "job_id": job_id}


@api.get("/projects/{pid}/batch")
async def get_batch(pid: str):
    doc = await projects_col.find_one({"id": pid}, {"_id": 0, "batch": 1})
    if not doc:
        raise HTTPException(404, "Project not found")
    return doc.get("batch") or {"running": False}


@api.get("/projects/{pid}/batch/stream")
async def batch_stream(pid: str):
    """Server-Sent Events stream of batch progress. Sends one event every ~1s
    until the job is not running, then a final 'done' event and closes."""
    doc = await projects_col.find_one({"id": pid}, {"_id": 0, "batch": 1})
    if not doc:
        raise HTTPException(404, "Project not found")

    async def event_gen():
        last_json = None
        stable_done_ticks = 0
        while True:
            d = await projects_col.find_one({"id": pid}, {"_id": 0, "batch": 1, "dub_job": 1})
            payload = {
                "batch": d.get("batch") if d else None,
                "dub_job": d.get("dub_job") if d else None,
            }
            cur = json.dumps(payload, default=str)
            if cur != last_json:
                yield f"event: progress\ndata: {cur}\n\n"
                last_json = cur
            running = (payload["batch"] or {}).get("running") or (payload["dub_job"] or {}).get("running")
            if not running:
                stable_done_ticks += 1
                # Send a final 'done' event and close after ~2 ticks of idle
                if stable_done_ticks >= 2:
                    yield f"event: done\ndata: {cur}\n\n"
                    return
            else:
                stable_done_ticks = 0
            await asyncio.sleep(1.0)

    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ----------------------------------------------------------------------------
# Multilingual auto-dub — render the final film into N language variants
# ----------------------------------------------------------------------------

async def _dub_worker(pid: str, languages: list[str], voice_override: Optional[str]):
    doc = await projects_col.find_one({"id": pid})
    if not doc:
        return
    scenes = doc.get("scenes") or []
    if not scenes:
        await projects_col.update_one({"id": pid}, {"$set": {"dub_job.running": False, "dub_job.errors": ["No scenes"]}})
        return

    # Steps per language: N scenes translated + N narrated + N muxed + 1 concat = 3N+1
    per_lang_steps = 3 * len(scenes) + 1
    total = per_lang_steps * len(languages)
    completed = 0
    errors: list[str] = []

    await projects_col.update_one(
        {"id": pid},
        {"$set": {"dub_job": {
            "running": True, "languages": languages, "total": total, "completed": 0,
            "current": "starting", "errors": [], "started_at": now_iso(), "finished_at": None,
            "results": [],
        }}},
    )

    default_voice = voice_override or doc.get("voice") or "onyx"
    default_model = doc.get("voice_model") or "tts-1"
    dub_characters = doc.get("characters") or []
    dub_narrator_voice = (
        (doc.get("blueprint") or {}).get("narrator_voice")
        or default_voice
        or "fable"
    )

    all_results = []
    for lang in languages:
        safe_lang = re.sub(r"[^a-zA-Z0-9]", "_", lang)[:16] or "lang"
        try:
            # Step 1: Translate each scene narration, then TTS, then mux
            per_scene_files = []
            per_scene_narr = []
            for scene in scenes:
                sid = scene.get("id")
                orig = scene.get("narration") or scene.get("description") or ""

                await projects_col.update_one(
                    {"id": pid},
                    {"$set": {"dub_job.current": f"{lang}:{sid}:translate"}},
                )
                try:
                    translated = await ai_services.translate_narration(orig, lang)
                except Exception as e:
                    translated = orig
                    errors.append(f"{lang}:{sid}:translate: {str(e)[:120]}")
                completed += 1
                await projects_col.update_one({"id": pid}, {"$set": {"dub_job.completed": completed}})

                await projects_col.update_one(
                    {"id": pid},
                    {"$set": {"dub_job.current": f"{lang}:{sid}:tts"}},
                )
                tts_name = f"{pid}_dub_{safe_lang}_scene_{sid}.mp3"
                dialogue_lines = scene.get("dialogue_lines") or []
                tts_ok = False
                if isinstance(dialogue_lines, list) and any((ln or {}).get("text") for ln in dialogue_lines):
                    # Translate each dialogue line into the target language and re-speak
                    # in each speaker's own voice
                    try:
                        translated_lines = []
                        for ln in dialogue_lines:
                            t = (ln.get("text") or "").strip()
                            if not t:
                                continue
                            try:
                                tr = await ai_services.translate_narration(t, lang)
                            except Exception:
                                tr = t
                            translated_lines.append({
                                "speaker": ln.get("speaker") or "narrator",
                                "text": tr or t,
                            })
                        if translated_lines:
                            await ai_services.generate_scene_audio_multivoice(
                                translated_lines, dub_characters, dub_narrator_voice,
                                tts_name, model=default_model,
                            )
                            tts_ok = True
                    except Exception as e:
                        errors.append(f"{lang}:{sid}:tts-multi: {str(e)[:120]}")

                if not tts_ok:
                    try:
                        await ai_services.generate_narration(
                            translated, tts_name, voice=default_voice, model=default_model,
                        )
                    except Exception as e:
                        errors.append(f"{lang}:{sid}:tts: {str(e)[:120]}")
                        tts_name = None
                completed += 1
                await projects_col.update_one({"id": pid}, {"$set": {"dub_job.completed": completed}})

                await projects_col.update_one(
                    {"id": pid},
                    {"$set": {"dub_job.current": f"{lang}:{sid}:mux"}},
                )
                scene_video = scene.get("video_file")
                if not scene_video:
                    errors.append(f"{lang}:{sid}:mux: no video_file — run Auto-Pilot first")
                    completed += 1
                    await projects_col.update_one({"id": pid}, {"$set": {"dub_job.completed": completed}})
                    continue
                mux_name = f"{pid}_dub_{safe_lang}_scene_{sid}_final.mp4"
                try:
                    await asyncio.to_thread(
                        assembly.mux_scene,
                        scene_video, tts_name, mux_name, None,  # subtitles come via SRT concat step, not burned-in
                    )
                    per_scene_files.append(mux_name)
                    per_scene_narr.append(translated)
                except Exception as e:
                    errors.append(f"{lang}:{sid}:mux: {str(e)[:120]}")
                completed += 1
                await projects_col.update_one({"id": pid}, {"$set": {"dub_job.completed": completed}})

            # Concat + subs
            await projects_col.update_one(
                {"id": pid},
                {"$set": {"dub_job.current": f"{lang}:assemble"}},
            )
            if per_scene_files:
                film_name = f"{pid}_dub_{safe_lang}_film.mp4"
                srt_name = f"{pid}_dub_{safe_lang}.srt"
                try:
                    await asyncio.to_thread(
                        assembly.concat_with_subs, per_scene_files, per_scene_narr, film_name, srt_name,
                    )
                    size_bytes = (STORAGE_DIR / film_name).stat().st_size
                    all_results.append({
                        "language": lang,
                        "film_file": film_name,
                        "srt_file": srt_name,
                        "size_bytes": size_bytes,
                        "size_mb": round(size_bytes / (1024 * 1024), 2),
                        "created_at": now_iso(),
                    })
                except Exception as e:
                    errors.append(f"{lang}:assemble: {str(e)[:200]}")
            completed += 1
            await projects_col.update_one(
                {"id": pid},
                {"$set": {"dub_job.completed": completed, "dub_job.errors": errors, "dub_job.results": all_results}},
            )
        except Exception as e:
            errors.append(f"{lang}: {str(e)[:200]}")

    # Merge with existing dubs (overwrite by language)
    existing = (await projects_col.find_one({"id": pid})).get("dubs") or []
    by_lang = {d.get("language"): d for d in existing}
    for r in all_results:
        by_lang[r["language"]] = r
    merged = list(by_lang.values())

    await projects_col.update_one(
        {"id": pid},
        {"$set": {
            "dubs": merged,
            "dub_job.running": False,
            "dub_job.finished_at": now_iso(),
            "dub_job.current": "done",
            "dub_job.errors": errors,
        }},
    )


@api.post("/projects/{pid}/dub")
async def start_dub(pid: str, body: DubRequest):
    doc = await projects_col.find_one({"id": pid})
    if not doc:
        raise HTTPException(404, "Project not found")
    scenes = doc.get("scenes") or []
    if not scenes:
        raise HTTPException(400, "Analyze the story first")
    # Ensure at least each scene has a video_file
    missing = [s.get("id") for s in scenes if not s.get("video_file")]
    if missing:
        raise HTTPException(400, f"These scenes have no video yet: {missing}. Run Auto-Pilot first.")
    langs = [lang.strip() for lang in (body.languages or []) if lang and lang.strip()]
    if not langs:
        raise HTTPException(400, "Provide at least one target language")
    if len(langs) > 10:
        raise HTTPException(400, "Max 10 languages per dub job")
    if (doc.get("dub_job") or {}).get("running"):
        return {"ok": True, "already_running": True}
    asyncio.create_task(_dub_worker(pid, langs, body.voice))
    return {"ok": True, "languages": langs}


@api.get("/projects/{pid}/dubs")
async def list_dubs(pid: str):
    doc = await projects_col.find_one({"id": pid}, {"_id": 0, "dubs": 1, "dub_job": 1})
    if not doc:
        raise HTTPException(404, "Project not found")
    return {"dubs": doc.get("dubs") or [], "dub_job": doc.get("dub_job")}


@api.get("/projects/{pid}/dubs/{language}/film")
async def download_dub(pid: str, language: str, user_id: str = ""):
    """Gated dub download — same paywall rules as the primary film."""
    doc = await projects_col.find_one({"id": pid}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Project not found")
    if not (doc.get("paid") or doc.get("free_granted")):
        raise HTTPException(402, "Film not unlocked — please unlock the primary film first")
    dubs = doc.get("dubs") or []
    match = next((d for d in dubs if d.get("language") == language), None)
    if not match:
        raise HTTPException(404, f"No dub for language: {language}")
    path = STORAGE_DIR / match["film_file"]
    if not path.exists():
        raise HTTPException(404, "Dub file missing on disk")
    safe_title = (doc.get("title") or "aipillu-film").replace("/", "-")[:60]
    safe_lang = re.sub(r"[^a-zA-Z0-9]", "_", language)[:16]
    return FileResponse(str(path), media_type="video/mp4", filename=f"{safe_title}_{safe_lang}.mp4")


@api.get("/projects/{pid}/subtitles")
async def download_subs(pid: str, language: str = ""):
    """Return the SRT subtitle file. If `language` is provided and a dub exists, returns the dub's SRT.
    Otherwise returns the primary film SRT (public — subs alone are not gated)."""
    doc = await projects_col.find_one({"id": pid}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Project not found")
    srt_file = None
    if language:
        dubs = doc.get("dubs") or []
        match = next((d for d in dubs if d.get("language") == language), None)
        if not match:
            raise HTTPException(404, f"No dub for language: {language}")
        srt_file = match.get("srt_file")
    else:
        srt_file = doc.get("final_srt")
    if not srt_file:
        raise HTTPException(404, "No subtitles available")
    path = STORAGE_DIR / srt_file
    if not path.exists():
        raise HTTPException(404, "Subtitle file missing")
    return FileResponse(str(path), media_type="application/x-subrip", filename=srt_file)


# ----------------------------------------------------------------------------
# Public gallery + Tips
# ----------------------------------------------------------------------------

@api.post("/projects/{pid}/publish")
async def publish_project(pid: str, body: PublishRequest):
    doc = await projects_col.find_one({"id": pid})
    if not doc:
        raise HTTPException(404, "Project not found")
    if body.is_public and not (doc.get("paid") or doc.get("free_granted")):
        raise HTTPException(402, "Unlock the film before making it public")
    if body.is_public and not doc.get("final_film"):
        raise HTTPException(400, "Assemble the film first")
    updates = {
        "is_public": bool(body.is_public),
        "tip_vpa": (body.tip_vpa or "").strip()[:64] or None,
        "updated_at": now_iso(),
    }
    if body.is_public:
        updates["published_at"] = now_iso()
    await projects_col.update_one({"id": pid}, {"$set": updates})
    return {"ok": True, "is_public": updates["is_public"]}


@api.get("/gallery")
async def gallery(limit: int = 30):
    limit = max(1, min(60, limit))
    cursor = projects_col.find(
        {"is_public": True, "final_film": {"$ne": None}},
        {"_id": 0}
    ).sort("published_at", -1).limit(limit)
    items = []
    async for d in cursor:
        items.append({
            "id": d["id"],
            "title": d.get("title") or "Untitled",
            "logline": (d.get("blueprint") or {}).get("logline") or "",
            "genre": (d.get("blueprint") or {}).get("genre") or "",
            "tone": (d.get("blueprint") or {}).get("tone") or "",
            "scene_count": len(d.get("scenes") or []),
            "views": d.get("views") or 0,
            "tips_total_inr": d.get("tips_total_inr") or 0,
            "tip_vpa": d.get("tip_vpa"),
            "poster_scene_image": next(
                (s.get("image_file") for s in (d.get("scenes") or []) if s.get("image_file")),
                None,
            ),
            "published_at": d.get("published_at"),
        })
    return items


@api.get("/gallery/{pid}")
async def gallery_item(pid: str):
    doc = await projects_col.find_one({"id": pid, "is_public": True}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Film not found or not public")
    # Increment views (fire and forget)
    await projects_col.update_one({"id": pid}, {"$inc": {"views": 1}})
    return {
        "id": doc["id"],
        "title": doc.get("title"),
        "logline": (doc.get("blueprint") or {}).get("logline") or "",
        "genre": (doc.get("blueprint") or {}).get("genre") or "",
        "tone": (doc.get("blueprint") or {}).get("tone") or "",
        "tip_vpa": doc.get("tip_vpa"),
        "views": (doc.get("views") or 0) + 1,
        "tips_total_inr": doc.get("tips_total_inr") or 0,
        "scenes": [
            {"id": s.get("id"), "title": s.get("title"), "image_file": s.get("image_file")}
            for s in (doc.get("scenes") or [])
        ],
        "final_film_available": bool(doc.get("final_film")),
    }


@api.get("/gallery/{pid}/stream")
async def gallery_stream(pid: str):
    """Public film stream — only for published projects."""
    doc = await projects_col.find_one({"id": pid, "is_public": True}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Film not found or not public")
    final_film = doc.get("final_film")
    if not final_film:
        raise HTTPException(404, "No film file")
    path = STORAGE_DIR / final_film
    if not path.exists():
        raise HTTPException(404, "File missing")
    return FileResponse(str(path), media_type="video/mp4")


@api.post("/gallery/{pid}/tip")
async def tip_creator(pid: str, body: TipRequest):
    doc = await projects_col.find_one({"id": pid, "is_public": True})
    if not doc:
        raise HTTPException(404, "Film not found or not public")

    amount = float(body.amount_inr or 0)
    if amount < 49:
        raise HTTPException(400, "Minimum tip is ₹49")
    if amount > 10000:
        raise HTTPException(400, "Maximum tip is ₹10,000")

    origin = body.origin_url.rstrip("/")
    success_url = f"{origin}/gallery/{pid}?tip_session_id={{CHECKOUT_SESSION_ID}}&tipped=1"
    cancel_url = f"{origin}/gallery/{pid}?tipped=0"
    webhook_host = os.getenv("APP_URL") or origin

    try:
        session = await payments.create_checkout(
            webhook_host_url=webhook_host,
            amount_inr=amount,
            project_id=pid,
            user_id=body.user_id,
            success_url=success_url,
            cancel_url=cancel_url,
        )
    except Exception as e:
        raise HTTPException(500, f"Tip checkout failed: {e}")

    await payments_col.insert_one({
        "project_id": pid,
        "user_id": body.user_id,
        "session_id": session.session_id,
        "amount": amount,
        "currency": "inr",
        "purpose": "tip",
        "message": (body.message or "")[:200],
        "payment_status": "initiated",
        "status": "pending",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    })
    return {"ok": True, "url": session.url, "session_id": session.session_id, "amount_inr": amount}


@api.get("/tip/status/{session_id}")
async def tip_status(session_id: str):
    tx = await payments_col.find_one({"session_id": session_id, "purpose": "tip"})
    if not tx:
        raise HTTPException(404, "Tip session not found")
    webhook_host = os.getenv("APP_URL", "")
    try:
        status = await payments.get_status(webhook_host, session_id)
    except Exception as e:
        raise HTTPException(500, f"Status check failed: {e}")

    await payments_col.update_one(
        {"session_id": session_id},
        {"$set": {
            "status": status.status,
            "payment_status": status.payment_status,
            "updated_at": now_iso(),
        }},
    )

    if status.payment_status == "paid" and tx.get("payment_status") != "paid":
        pid = tx.get("project_id")
        amount = tx.get("amount") or 0
        if pid:
            await projects_col.update_one(
                {"id": pid},
                {"$inc": {"tips_total_inr": float(amount)}},
            )
        await payments_col.update_one(
            {"session_id": session_id},
            {"$set": {"payment_status": "paid"}},
        )

    return {
        "session_id": session_id,
        "status": status.status,
        "payment_status": status.payment_status,
        "amount_total": status.amount_total,
        "currency": status.currency,
        "project_id": tx.get("project_id"),
    }


@api.get("/voice-preview")
async def voice_preview(voice: str = "onyx", model: str = "tts-1", language: str = ""):
    """Return a short (~5s) TTS sample for the given voice/language.
    Cached on disk under storage/preview_{voice}_{model}_{lang}.mp3 so repeated hits are instant."""
    ALLOWED_VOICES = {"alloy", "ash", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer"}
    if voice not in ALLOWED_VOICES:
        raise HTTPException(400, f"voice must be one of {sorted(ALLOWED_VOICES)}")
    if model not in {"tts-1", "tts-1-hd"}:
        raise HTTPException(400, "model must be tts-1 or tts-1-hd")

    lang_key = (language or "auto").strip().lower()[:16] or "auto"
    safe_lang = re.sub(r"[^a-z0-9]", "_", lang_key)
    fname = f"preview_{voice}_{model}_{safe_lang}.mp3"
    path = STORAGE_DIR / fname

    if not path.exists():
        # Pick a sample line in the requested language (or English fallback)
        SAMPLES = {
            "auto": "Every story deserves a screen. Roll the first cut.",
            "en": "Every story deserves a screen. Roll the first cut.",
            "hi": "हर कहानी को एक परदा चाहिए। पहला दृश्य शुरू करें।",
            "bn": "প্রতিটি গল্পের একটি পর্দা প্রাপ্য।",
            "ta": "ஒவ்வொரு கதைக்கும் ஒரு திரை தேவை.",
            "te": "ప్రతి కథకూ ఒక తెర కావాలి.",
            "mr": "प्रत्येक कथेला एक पडदा हवा असतो.",
            "gu": "દરેક વાર્તાને એક પડદો જોઈએ.",
            "kn": "ಪ್ರತಿ ಕಥೆಗೂ ಒಂದು ಪರದೆ ಬೇಕು.",
            "ml": "എല്ലാ കഥയ്ക്കും ഒരു തിരശ്ശീല വേണം.",
            "pa": "ਹਰ ਕਹਾਣੀ ਨੂੰ ਇੱਕ ਪਰਦਾ ਚਾਹੀਦਾ ਹੈ.",
            "ur": "ہر کہانی کو ایک پردہ چاہیے۔",
            "sa": "प्रत्येकस्य कथायाः एकं पटलम् आवश्यकम्।",
            "ne": "हरेक कथाले पर्दा माग्छ।",
            "ar": "كل قصة تستحق شاشة.",
            "he": "לכל סיפור מגיע מסך.",
            "fa": "هر داستان لایق یک صفحه است.",
            "tr": "Her hikaye bir perdeyi hak eder.",
            "ru": "Каждой истории — свой экран.",
            "uk": "Кожній історії — свій екран.",
            "es": "Cada historia merece una pantalla.",
            "fr": "Chaque histoire mérite un écran.",
            "de": "Jede Geschichte verdient eine Leinwand.",
            "it": "Ogni storia merita uno schermo.",
            "pt": "Toda história merece uma tela.",
            "nl": "Elk verhaal verdient een scherm.",
            "pl": "Każda historia zasługuje na ekran.",
            "ja": "すべての物語にスクリーンを。",
            "zh": "每一个故事都值得一个屏幕。",
            "yue": "每一個故事都值得一個屏幕。",
            "ko": "모든 이야기에는 화면이 필요합니다.",
            "vi": "Mỗi câu chuyện xứng đáng có một màn ảnh.",
            "th": "ทุกเรื่องราวสมควรมีจอ.",
            "id": "Setiap cerita layak mendapat layar.",
            "ms": "Setiap kisah berhak mendapat layar.",
            "tl": "Bawat kuwento ay karapat-dapat sa tabing.",
            "sw": "Kila hadithi inastahili skrini.",
            "am": "እያንዳንዱ ታሪክ ማያ ገጽ ይገባዋል.",
            "yo": "Gbogbo ìtàn yẹ láti wà lórí àwòrán.",
            "zu": "Yonke indaba iyalifanela iskrini.",
            "af": "Elke storie verdien 'n skerm.",
        }
        sample_text = SAMPLES.get(lang_key)
        if not sample_text:
            # For any language not in the map, ask Claude Haiku to translate the English line quickly
            try:
                sample_text = await ai_services.translate_narration(
                    SAMPLES["en"], language or "English"
                )
            except Exception:
                sample_text = SAMPLES["en"]

        try:
            await ai_services.generate_narration(sample_text, fname, voice=voice, model=model)
        except Exception as e:
            raise HTTPException(500, f"Preview generation failed: {e}")

    return FileResponse(str(path), media_type="audio/mpeg", filename=fname)


def _media_type(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".mp4"):
        return "video/mp4"
    if lower.endswith(".webm"):
        return "video/webm"
    if lower.endswith(".mp3"):
        return "audio/mpeg"
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    if lower.endswith(".srt"):
        return "application/x-subrip"
    return "application/octet-stream"


def _range_response(path: Path, media: str, request: Request) -> Response:
    """Serve a file with HTTP Range support (required for HTML5 <video> to play reliably).
    Handles the Range header and returns 206 Partial Content when present, else 200 with full file."""
    file_size = path.stat().st_size
    range_header = request.headers.get("range") or request.headers.get("Range")

    if request.method == "HEAD":
        return Response(
            status_code=200,
            headers={
                "Content-Type": media,
                "Content-Length": str(file_size),
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=3600",
            },
        )

    if range_header:
        # Parse "bytes=start-end"
        try:
            units, _, rng = range_header.partition("=")
            if units.strip().lower() == "bytes":
                start_str, _, end_str = rng.strip().partition("-")
                start = int(start_str) if start_str else 0
                end = int(end_str) if end_str else file_size - 1
                if start < 0 or start >= file_size:
                    raise ValueError("start out of range")
                end = min(end, file_size - 1)
                length = end - start + 1

                def stream():
                    with open(path, "rb") as f:
                        f.seek(start)
                        remaining = length
                        chunk_size = 64 * 1024
                        while remaining > 0:
                            data = f.read(min(chunk_size, remaining))
                            if not data:
                                break
                            remaining -= len(data)
                            yield data

                return StreamingResponse(
                    stream(),
                    status_code=206,
                    media_type=media,
                    headers={
                        "Content-Range": f"bytes {start}-{end}/{file_size}",
                        "Accept-Ranges": "bytes",
                        "Content-Length": str(length),
                        "Cache-Control": "public, max-age=3600",
                    },
                )
        except Exception:
            # Fall through to full response
            pass

    # No Range header (or bad one) — full body with Accept-Ranges so browsers can retry with Range
    def full_stream():
        with open(path, "rb") as f:
            while True:
                chunk = f.read(64 * 1024)
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(
        full_stream(),
        media_type=media,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Cache-Control": "public, max-age=3600",
        },
    )


@api.api_route("/storage/{filename}", methods=["GET", "HEAD"])
async def get_asset(filename: str, request: Request):
    # Basic path traversal protection
    if "/" in filename or ".." in filename:
        raise HTTPException(400, "Invalid filename")
    # Final film downloads must go through the paywall endpoint
    if filename.endswith("_final_film.mp4"):
        raise HTTPException(402, "Final film requires unlock via /projects/{id}/film")
    path = STORAGE_DIR / filename
    if not path.exists():
        raise HTTPException(404, "File not found")
    return _range_response(path, _media_type(filename), request)


# ----------------------------------------------------------------------------
# Paywall / Unlock / Sharing
# ----------------------------------------------------------------------------

async def _user_has_free_tier_used(user_id: str) -> bool:
    """A user gets ONE free ≤20MB film. After that, everything must be paid."""
    if not user_id:
        return True
    count = await projects_col.count_documents(
        {"free_granted": True, "created_by": user_id}
    )
    return count > 0


@api.get("/projects/{pid}/unlock-status")
async def unlock_status(pid: str, user_id: str = ""):
    doc = await projects_col.find_one({"id": pid}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Project not found")

    final_film = doc.get("final_film")
    breakdown = payments.compute_price_breakdown(doc)

    already_unlocked = bool(doc.get("paid") or doc.get("free_granted"))
    size_bytes = payments.get_film_size_bytes(final_film)

    # Determine free eligibility
    free_eligible = False
    reason = ""
    if not final_film:
        reason = "No final film yet"
    elif already_unlocked:
        reason = "Already unlocked"
        free_eligible = False
    else:
        under_limit = size_bytes <= payments.FREE_TIER_MAX_BYTES
        used_free = await _user_has_free_tier_used(user_id)
        if under_limit and not used_free:
            free_eligible = True
            reason = "Free tier: first film under 20 MB"
        elif under_limit and used_free:
            reason = "Free tier already used — payment required"
        else:
            reason = "Film exceeds 20 MB — payment required"

    return {
        "project_id": pid,
        "has_final_film": bool(final_film),
        "size_bytes": size_bytes,
        "size_mb": round(size_bytes / (1024 * 1024), 2),
        "already_unlocked": already_unlocked,
        "free_eligible": free_eligible,
        "requires_payment": bool(final_film) and not already_unlocked and not free_eligible,
        "reason": reason,
        "price": breakdown,
        "unlocked_via": "paid" if doc.get("paid") else ("free" if doc.get("free_granted") else None),
    }


@api.post("/projects/{pid}/claim-free")
async def claim_free(pid: str, body: CheckoutRequest):
    """Consume the user's one free unlock, if eligible."""
    doc = await projects_col.find_one({"id": pid})
    if not doc:
        raise HTTPException(404, "Project not found")
    if doc.get("paid") or doc.get("free_granted"):
        return {"ok": True, "already_unlocked": True}
    final_film = doc.get("final_film")
    if not final_film:
        raise HTTPException(400, "Assemble the film first")

    size = payments.get_film_size_bytes(final_film)
    if size > payments.FREE_TIER_MAX_BYTES:
        raise HTTPException(402, "Film exceeds 20 MB free tier — payment required")

    if await _user_has_free_tier_used(body.user_id):
        raise HTTPException(402, "Free tier already used for this browser — payment required")

    await projects_col.update_one(
        {"id": pid},
        {"$set": {
            "free_granted": True,
            "created_by": body.user_id,
            "unlocked_at": now_iso(),
        }},
    )
    return {"ok": True, "free_granted": True}


@api.post("/projects/{pid}/checkout")
async def create_checkout_session(pid: str, body: CheckoutRequest):
    doc = await projects_col.find_one({"id": pid})
    if not doc:
        raise HTTPException(404, "Project not found")
    if doc.get("paid") or doc.get("free_granted"):
        return {"ok": True, "already_unlocked": True}
    if not doc.get("final_film"):
        raise HTTPException(400, "Assemble the film first")

    price = payments.compute_price_inr(doc)
    origin = body.origin_url.rstrip("/")
    success_url = f"{origin}/studio/{pid}?session_id={{CHECKOUT_SESSION_ID}}&paid=1"
    cancel_url = f"{origin}/studio/{pid}?paid=0"

    # Use APP_URL for webhook host so Stripe can reach us
    webhook_host = os.getenv("APP_URL") or origin

    try:
        session = await payments.create_checkout(
            webhook_host_url=webhook_host,
            amount_inr=price,
            project_id=pid,
            user_id=body.user_id,
            success_url=success_url,
            cancel_url=cancel_url,
        )
    except Exception as e:
        raise HTTPException(500, f"Stripe checkout failed: {e}")

    # Store payment transaction record (pending)
    await payments_col.insert_one({
        "project_id": pid,
        "user_id": body.user_id,
        "session_id": session.session_id,
        "amount": price,
        "currency": "inr",
        "payment_status": "initiated",
        "status": "pending",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    })
    await projects_col.update_one({"id": pid}, {"$set": {"price_inr": price}})

    return {"ok": True, "url": session.url, "session_id": session.session_id, "amount_inr": price}


@api.get("/checkout/status/{session_id}")
async def checkout_status(session_id: str):
    """Poll checkout status. Idempotently marks the project as paid when payment succeeds."""
    tx = await payments_col.find_one({"session_id": session_id})
    if not tx:
        raise HTTPException(404, "Session not found")

    # Query Stripe for current status
    webhook_host = os.getenv("APP_URL", "")
    try:
        status = await payments.get_status(webhook_host, session_id)
    except Exception as e:
        raise HTTPException(500, f"Stripe status check failed: {e}")

    await payments_col.update_one(
        {"session_id": session_id},
        {"$set": {
            "status": status.status,
            "payment_status": status.payment_status,
            "amount_total": status.amount_total,
            "updated_at": now_iso(),
        }},
    )

    # Idempotently unlock project
    if status.payment_status == "paid" and tx.get("payment_status") != "paid":
        pid = tx.get("project_id")
        if pid:
            await projects_col.update_one(
                {"id": pid},
                {"$set": {"paid": True, "unlocked_at": now_iso(), "created_by": tx.get("user_id")}},
            )
        await payments_col.update_one(
            {"session_id": session_id},
            {"$set": {"payment_status": "paid"}},
        )

    return {
        "session_id": session_id,
        "status": status.status,
        "payment_status": status.payment_status,
        "amount_total": status.amount_total,
        "currency": status.currency,
        "project_id": tx.get("project_id"),
    }


@app.post("/api/webhook/stripe")
async def stripe_webhook(request: __import__("fastapi").Request):
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    webhook_host = os.getenv("APP_URL", "")
    try:
        event = await payments.handle_webhook(webhook_host, body, signature)
    except Exception as e:
        logger.error(f"Webhook verification failed: {e}")
        raise HTTPException(400, "Invalid signature")

    if event.payment_status == "paid":
        session_id = event.session_id
        tx = await payments_col.find_one({"session_id": session_id})
        if tx and tx.get("payment_status") != "paid":
            pid = tx.get("project_id")
            if pid:
                await projects_col.update_one(
                    {"id": pid},
                    {"$set": {"paid": True, "unlocked_at": now_iso(), "created_by": tx.get("user_id")}},
                )
            await payments_col.update_one(
                {"session_id": session_id},
                {"$set": {"payment_status": "paid", "status": "complete", "updated_at": now_iso()}},
            )
    return {"received": True}


@api.get("/projects/{pid}/film")
async def download_film(pid: str, user_id: str = ""):
    """Gated download endpoint for the final film."""
    doc = await projects_col.find_one({"id": pid}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Project not found")
    final_film = doc.get("final_film")
    if not final_film:
        raise HTTPException(404, "No final film assembled yet")
    if not (doc.get("paid") or doc.get("free_granted")):
        raise HTTPException(402, "Film not unlocked — please unlock (free or paid)")

    path = STORAGE_DIR / final_film
    if not path.exists():
        raise HTTPException(404, "Film file missing on disk")
    safe_title = (doc.get("title") or "aipillu-film").replace("/", "-")[:60]
    return FileResponse(str(path), media_type="video/mp4", filename=f"{safe_title}.mp4")


@api.get("/projects/{pid}/share-info")
async def share_info(pid: str, origin_url: str = ""):
    """Return a shareable public URL + title for the film. Only if unlocked."""
    doc = await projects_col.find_one({"id": pid}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Project not found")
    if not (doc.get("paid") or doc.get("free_granted")):
        raise HTTPException(402, "Unlock the film before sharing")
    if not doc.get("final_film"):
        raise HTTPException(404, "No final film")

    base = os.getenv("APP_URL") or origin_url.rstrip("/")
    file_url = f"{base}/api/projects/{pid}/film"
    return {
        "share_url": file_url,
        "title": doc.get("title") or "My AI Film",
        "logline": (doc.get("blueprint") or {}).get("logline") or "Made with AiPillu Studio",
    }


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def _shutdown():
    client.close()
