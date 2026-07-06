# AiPillu Studio — Story-to-Film AI Agent

## Original Problem Statement
Create an AI agent that converts any story (input via PDF/DOC/DOCX, voice, URL, or pasted script) into a video film with original AI-generated characters (copyright-safe). Stories can be Ramayan, Mahabharat, Shiva, or any story from anywhere. Users can download the video and share on YouTube/WhatsApp/Instagram/Twitter/X. First video free to share up to 20 MB; further sharing/download requires payment via UPI. Payments must be secured and received via UPI. Include 5-10% profit margin for creator. Push code to GitHub.

## Architecture
- **Backend**: FastAPI + MongoDB + ffmpeg (Python)
- **Frontend**: React (CRA) + TailwindCSS + Framer Motion + Lucide icons
- **AI stack** (all via Emergent Universal Key):
  - Claude Sonnet 4.6 — story blueprint (characters, scenes) with copyright-safe rewriting
  - Gemini Nano Banana — character portraits + scene storyboard images
  - OpenAI Sora 2 — text-to-video clips (4/8/12s)
  - OpenAI TTS (tts-1) — narration (English/Hindi/multi-lingual)
  - OpenAI Whisper — voice input transcription
- **Ingestion**: PDF (pypdf), DOCX (python-docx), TXT, URL (httpx + BeautifulSoup), Voice (Whisper)
- **Assembly**: ffmpeg concat + drawtext subtitles + optional Ken-Burns pan/zoom for image-only scenes
- **Payments**: Stripe Checkout (UPI + Card) via emergentintegrations; server-side pricing; HMAC-verified webhook + polling fallback
- **Storage**: Local files under `/app/backend/storage`, gated download for final films

## Pricing Formula (server-side)
`price_INR = ceil( (₹10 base + ₹2/MB over 20 MB + ₹5 per Sora 2 scene) × 1.10 )`, floor at ₹49 (Stripe INR minimum ~$0.50).
- First film free if final MP4 ≤ 20 MB AND user (anonymous localStorage uid) has no prior free unlock
- Everything else paid

## What's Implemented (2026-07-06)
### Backend endpoints (`/api`)
- Health / CORS / project CRUD
- Ingestion: `/ingest/text`, `/ingest/url`, `/ingest/file`, `/ingest/voice`
- Analysis: `/analyze` (async background job to bypass 100s Cloudflare timeout)
- Generation: character image, scene image, Sora 2 video, Ken-Burns video, TTS narration, per-scene mux, full-film assemble
- Paywall: `/unlock-status`, `/claim-free`, `/checkout`, `/checkout/status/{sid}`, `/webhook/stripe`
- Gated download: `/projects/{pid}/film`, `/projects/{pid}/share-info`
- Guarded storage: `_final_film.mp4` files always require unlock

### Frontend
- Landing page: cinematic dark/gold theme (Outfit + Manrope), asymmetric hero, 6-step how-it-works, copyright safety section
- Studio (single-page workspace):
  - Sidebar: project list + create/delete
  - Tabs: Ingest / Characters / Scenes / Assemble
  - Ingest tab: 4 modes (Script, File, URL, Voice) + source preview + "Analyze" button
  - Characters tab: portrait grid with generate/regenerate
  - Scenes tab: per-scene image + video (Sora 2 or Ken-Burns) + narration + mux
  - Assemble tab: final film preview, unlock/paywall UI, share panel (WhatsApp/Twitter/Facebook/Telegram/LinkedIn + Copy Link), YouTube/Instagram download tiles
- Anonymous user_id auto-generated in localStorage

### Security
- Server-side pricing (never trusted from client)
- Stripe HMAC signature verification on webhook
- Anonymous user isolation for free-tier accounting
- Final film gated behind explicit unlock

## Tested (iteration_1)
20 pass / 2 fail / 1 skip — bugs found and fixed:
1. Stripe INR min raised to ₹49
2. Wikipedia UA policy fixed
3. Long Claude call moved to background task with polling

## Backlog / Next actions
- P1: Frontend E2E test after fixes
- P1: Regression retest of backend (pricing floor, URL ingest, analyze polling)
- P2: Auth (currently anonymous localStorage uid)
- P2: Multi-language narration voice picker in UI
- P2: Batch scene-video generation with WebSocket progress
- P2: Instagram / YouTube direct upload via OAuth apps (weeks of approval)
- P3: Custom character reference-image upload
- P3: Save-to-GitHub link (already exists on Emergent platform)

## Enhancement idea
Add a **"Public Gallery"** page where paid films (with user consent) are showcased — drives shareable virality and secondary UPI monetization via "Tip the creator" buttons on popular films.

## Test Credentials
Anonymous (no login). `EMERGENT_LLM_KEY` and `STRIPE_API_KEY=sk_test_emergent` are in `/app/backend/.env`.
