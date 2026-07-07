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

## Update (2026-07-06 · 100+ languages)
- Frontend **LANGUAGES** list expanded from 16 → **97+ world languages** (all continents), grouped by region
- Narration language picker now appears **at the top of the Ingest panel** — applies to Paste-Script, Upload-File, From-URL, Voice/Audio inputs
- Backend accepts arbitrary language strings (full name like "Swahili"/"Zulu" or ISO code "sw"/"zu")
- Ingestion endpoints (`/ingest/text|url|file|voice`) all accept `language` and persist it to `project.language_hint`
- `/ingest/voice` maps full-name → ISO 639-1 code for Whisper (`ingestion.iso_code_for_language`)
- Analyze prompt to Claude now issues an explicit `LANGUAGE OVERRIDE` instruction with native-script guidance
- OpenAI TTS voices are multi-lingual by design — same voice speaks any language driven by the narration text
- Landing page copy updated to advertise 100+ world languages

## Update (2026-07-07 · Per-scene narration override + progress polish)
### Per-scene narration language override
- Scene model gains optional `language` field
- **PATCH /api/projects/{pid}/scenes/{sid}/narration** — accepts `narration` (text override) and/or `language` (translate existing text to that language). Empty body → 400.
- **POST /api/projects/{pid}/scenes/{sid}/narration** priority chain: request body `language` > scene `language` > project `language_hint`. Auto-translates + persists if scene stored a different language.
- New helper `ai_services.translate_narration()` — uses **Claude Haiku 4.5** for fast, cinematic-tone translation with native script (Devanagari, Arabic, Cyrillic, Han, Kana etc.). Graceful fallback to original text on model refusal.
- Frontend `SceneNarrationEditor` sub-component in Scenes tab: inline edit textarea + language dropdown (97+ langs) + Translate + Save buttons.

### Batch progress UI polish
- New `BatchProgressCard` with:
  - Animated status header (pulsing dot when running, step icon per action)
  - Real-time elapsed timer (mm:ss)
  - 2-digit percent, X/Y step count
  - Per-scene grid (2/4/6 cols responsive) with gold glow on current scene
  - Step-dot indicators per scene: image · audio · video · final
- Framer-motion smooth progress-bar animation with gradient (gold → yellow)

## Tested (iteration_3)
- 44/44 tests pass — 22 new + 22 regression
- Verified: PATCH edit, PATCH translate to Hindi with native script, chained language priority, translation persistence, audio_file/final_file cleared on text change, arbitrary language names accepted, all 3 previous regressions still fixed

## Update (2026-07-07 · Per-scene voice override + Voice preview player)
### Per-scene voice override
- Scene doc gains optional `voice` + `voice_model` fields (default: project-level or "onyx"/"tts-1")
- **POST /scenes/{sid}/narration** priority chain updated: body.voice > scene.voice > project.voice
- **PATCH /scenes/{sid}/narration** accepts `voice` and `voice_model` (independent of narration/language edits)
- Scene UI shows a `voice · <name>` pill when an override is set

### Voice preview (~5s sample player)
- **GET /api/voice-preview?voice=X&model=Y&language=Z** returns a cinematic sample line ("Every story deserves a screen. Roll the first cut.") in 40+ built-in languages, or Claude-Haiku translated for anything else
- Server-side caches sample MP3s at `storage/preview_<voice>_<model>_<lang>.mp3`; second call ~13× faster (0.13s vs 1.7s in live test)
- Frontend `VoicePreview` button added:
  - In Voice & Language settings panel (project-level default preview)
  - In SceneNarrationEditor next to the per-scene voice picker
- Uses HTML5 `Audio` element for playback with cached URL

## Tested (iteration_4 — frontend E2E)
- 28/28 assertions across 8 scenarios passed
- New voice-preview + per-scene voice override UI verified end-to-end
- Regression on Landing / Gallery / Studio still passes

## Update (2026-07-07 · Multilingual Auto-Dub + SRT + SSE)
### Multilingual Auto-Dub (revenue multiplier)
- New `POST /api/projects/{pid}/dub {languages: [...], voice?}` — background job renders full-film variants in up to 10 languages per call.
- Per-language pipeline: Claude Haiku translates each scene narration → OpenAI TTS in target language → ffmpeg re-mux per scene → concat with soft SRT subs → downloadable MP4.
- `GET /api/projects/{pid}/dubs` — list of `{language, film_file, srt_file, size_bytes, size_mb, created_at}`
- `GET /api/projects/{pid}/dubs/{lang}/film` — gated download (same paywall as primary film — single unlock covers all dubs).
- Project doc gains `dubs: []` and `dub_job: {running, total, completed, current, errors, results}`
- Frontend `DubPanel` in the Assemble tab (visible only after unlock): 16 popular languages as toggle chips, any custom language input, up to 10 languages per job, per-dub video preview + MP4 + SRT download.

### SRT subtitle track
- `assembly.build_srt` + `probe_duration` + `attach_soft_subs` helpers
- `assembly.concat_with_subs` — probes each clip's duration, emits time-accurate SRT (subtitle for the middle 80% of each scene), concatenates + embeds soft `mov_text` subtitle track in the MP4.
- `GET /api/projects/{pid}/subtitles?language=` — public SRT download (subs alone are not paywalled). Returns dub-specific SRT if `language=X`, else primary film SRT.
- `assemble_film` and Auto-Pilot's auto-assemble step both use `concat_with_subs` now (no more burned-in subs).
- Frontend adds an **SRT download button** alongside the MP4 button in the Share panel, plus per-dub MP4+SRT tiles.

### Server-Sent Events (SSE) for batch/dub progress
- `GET /api/projects/{pid}/batch/stream` — text/event-stream endpoint, emits `progress` events (JSON `{batch, dub_job}`) whenever state changes, ~1s tick, `done` event when both jobs idle for 2 ticks then closes.
- Frontend Batch panel and DubPanel both use `EventSource`; graceful fallback to polling on error.
- Reduces load: no more every-2.5s polling; instant scene-level updates.

## Verified live
- SSE endpoint streams events + done event correctly (curl -N test)
- Dub endpoint rejects requests with no scenes (400) and missing videos (400 with scene ids list)
- Subtitle download 404s cleanly when no film exists
- Zero JS console errors after full UI load
