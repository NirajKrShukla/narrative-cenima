"""Story-to-Film AI Agent — FastAPI backend."""
from __future__ import annotations
import os
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
from fastapi.responses import FileResponse, JSONResponse
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


class TextIngest(BaseModel):
    text: str


class AnalyzeRequest(BaseModel):
    language_hint: Optional[str] = "auto"


class GenerateVideoRequest(BaseModel):
    duration: int = 4  # 4, 8, or 12
    size: str = "1280x720"
    model: str = "sora-2"


class GenerateNarrationRequest(BaseModel):
    voice: str = "onyx"
    model: str = "tts-1"


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
        "status": "created",
        "paid": False,
        "free_granted": False,
        "unlocked_at": None,
        "price_inr": None,
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


async def _update_source(pid: str, text: str, source_type: str, meta: dict | None = None):
    if not text or len(text.strip()) < 30:
        raise HTTPException(400, "Extracted text is too short — please provide a richer source.")
    await projects_col.update_one(
        {"id": pid},
        {"$set": {
            "source_text": text[:40000],
            "source_type": source_type,
            "source_meta": meta or {},
            "status": "ingested",
            "updated_at": now_iso(),
        }},
    )


@api.post("/projects/{pid}/ingest/text")
async def ingest_text(pid: str, body: TextIngest):
    doc = await projects_col.find_one({"id": pid})
    if not doc:
        raise HTTPException(404, "Project not found")
    await _update_source(pid, body.text, "text")
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
    await _update_source(pid, text, "url", {"url": body.url})
    return {"ok": True, "chars": len(text)}


@api.post("/projects/{pid}/ingest/file")
async def ingest_file(pid: str, file: UploadFile = File(...)):
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
    await _update_source(pid, text, "file", {"filename": file.filename})
    return {"ok": True, "chars": len(text), "filename": file.filename}


@api.post("/projects/{pid}/ingest/voice")
async def ingest_voice(pid: str, file: UploadFile = File(...), language: Optional[str] = Form(None)):
    doc = await projects_col.find_one({"id": pid})
    if not doc:
        raise HTTPException(404, "Project not found")
    tmp = STORAGE_DIR / f"voice_{pid}_{uuid.uuid4().hex[:6]}_{file.filename}"
    tmp.write_bytes(await file.read())
    try:
        text = await ingestion.transcribe_audio(str(tmp), language=language)
    except Exception as e:
        raise HTTPException(400, f"Transcription failed: {e}")
    finally:
        try:
            tmp.unlink()
        except Exception:
            pass
    await _update_source(pid, text, "voice", {"filename": file.filename, "language": language})
    return {"ok": True, "chars": len(text), "transcript": text[:500]}


@api.post("/projects/{pid}/analyze")
async def analyze(pid: str, body: AnalyzeRequest = AnalyzeRequest()):
    doc = await projects_col.find_one({"id": pid})
    if not doc:
        raise HTTPException(404, "Project not found")
    if not doc.get("source_text"):
        raise HTTPException(400, "No source text ingested yet")

    await projects_col.update_one({"id": pid}, {"$set": {"status": "analyzing"}})
    try:
        blueprint = await ai_services.analyze_story(doc["source_text"], body.language_hint or "auto")
    except Exception as e:
        await projects_col.update_one({"id": pid}, {"$set": {"status": "error", "last_error": str(e)}})
        raise HTTPException(500, f"Story analysis failed: {e}")

    characters = blueprint.get("characters") or []
    scenes = blueprint.get("scenes") or []

    # Ensure ids exist
    for i, c in enumerate(characters):
        c["id"] = c.get("id") or f"char_{i+1}"
        c["image_file"] = None
    for i, s in enumerate(scenes):
        s["id"] = s.get("id") or f"scene_{i+1}"
        s["image_file"] = None
        s["video_file"] = None
        s["audio_file"] = None
        s["final_file"] = None

    await projects_col.update_one(
        {"id": pid},
        {"$set": {
            "blueprint": blueprint,
            "title": blueprint.get("title") or doc["title"],
            "characters": characters,
            "scenes": scenes,
            "status": "analyzed",
            "updated_at": now_iso(),
        }},
    )
    return await get_project(pid)


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
        f"No text, no logos, do not resemble any copyrighted franchise or real actor."
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
    text = scene.get("narration") or scene.get("description") or ""
    fname = f"{pid}_scene_{sid}.mp3"
    try:
        await ai_services.generate_narration(text, fname, voice=body.voice, model=body.model)
    except Exception as e:
        raise HTTPException(500, f"TTS failed: {e}")
    await projects_col.update_one(
        {"id": pid, "scenes.id": sid},
        {"$set": {"scenes.$.audio_file": fname, "updated_at": now_iso()}},
    )
    return {"ok": True, "audio_file": fname}


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
    # Use each scene's final_file if present, else video_file
    ordered = []
    for s in scenes:
        f = s.get("final_file") or s.get("video_file")
        if f:
            ordered.append(f)
    if not ordered:
        raise HTTPException(400, "No scene videos to assemble")
    fname = f"{pid}_final_film.mp4"
    try:
        await asyncio.to_thread(assembly.concat_scenes, ordered, fname)
    except Exception as e:
        raise HTTPException(500, f"Assembly failed: {e}")
    await projects_col.update_one(
        {"id": pid},
        {"$set": {"final_film": fname, "status": "assembled", "updated_at": now_iso()}},
    )
    return {"ok": True, "final_film": fname}


@api.get("/storage/{filename}")
async def get_asset(filename: str):
    # Basic path traversal protection
    if "/" in filename or ".." in filename:
        raise HTTPException(400, "Invalid filename")
    # Final film downloads must go through the paywall endpoint
    if filename.endswith("_final_film.mp4"):
        raise HTTPException(402, "Final film requires unlock via /projects/{id}/film")
    path = STORAGE_DIR / filename
    if not path.exists():
        raise HTTPException(404, "File not found")
    # infer media type
    lower = filename.lower()
    if lower.endswith(".mp4"):
        media = "video/mp4"
    elif lower.endswith(".mp3"):
        media = "audio/mpeg"
    elif lower.endswith(".png"):
        media = "image/png"
    elif lower.endswith(".jpg") or lower.endswith(".jpeg"):
        media = "image/jpeg"
    else:
        media = "application/octet-stream"
    return FileResponse(str(path), media_type=media, filename=filename)


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
    safe_title = (doc.get("title") or "kavya-film").replace("/", "-")[:60]
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
        "logline": (doc.get("blueprint") or {}).get("logline") or "Made with Kavya Studio",
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
