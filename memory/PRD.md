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

## Update (2026-07-07 · Homepage demo videos)
### Two branded demo videos on the landing page
- **demo_showcase.mp4** (18 s, 160 KB) — cinematic teaser: "Every story deserves a screen · Any language · Any source · Original characters · AiPillu Studio"
- **demo_workflow.mp4** (17 s, 177 KB) — six numbered pipeline steps (Ingest → Analyze → Cast → Animate → Narrate → Share) with descriptions
- Generated by `/app/backend/scripts/gen_demos.py` using ffmpeg lavfi + drawtext + drawbox (deterministic, no external deps, ~8s runtime)
- Both served publicly via `/api/storage/demo_*.mp4` (excluded from the paywall gate)
- Landing page adds a new **"See it in action"** section (`#demo`) with:
  - Two `DemoTile` cards with hover-to-play, click-to-fullscreen behavior
  - Large gold play-button overlay when paused
  - Framer-motion lift animation on hover
  - "Watch demo" nav link
  - CTA "Make your own — start free" below

### Files
- /app/backend/scripts/gen_demos.py — video generator script
- /app/backend/storage/demo_showcase.mp4
- /app/backend/storage/demo_workflow.mp4
- /app/frontend/src/pages/Landing.jsx — new #demo section + DemoTile component

## Verified live
- Both MP4s reachable via HTTPS with correct sizes (163570 + 181310 bytes)
- 2 `<video>` elements render, both playable (currentTime advances)
- All data-testids: `demo-showcase`, `demo-workflow`, `demo-showcase-video`, `demo-workflow-video`, `nav-demo`, `demo-cta`
- Landing lints clean, zero JS console errors

## Bugfix (2026-07-07 · Demo videos)
Three root-cause bugs prevented the demo videos from playing in real browsers:

1. **Backend: `Content-Disposition: attachment` header** — `FileResponse(filename=...)` was forcing download instead of inline `<video>` playback. **Fix**: removed the `filename=` param on `/api/storage/{filename}` for inline playback.

2. **Backend: HTTP 405 on HEAD requests** — `@api.get()` only accepts GET; browsers issue HEAD before playing videos. **Fix**: changed to `@api.api_route(methods=["GET","HEAD"])`.

3. **Backend: no HTTP Range support** — Starlette's `FileResponse` inside a route handler doesn't handle Range requests; served full 200 with 348 KB even when browser asked for the first 1 KB. Chrome refuses to play videos without proper `206 Partial Content` + `Accept-Ranges: bytes`. **Fix**: wrote a manual `_range_response()` helper that parses `Range` headers, streams the requested byte range with 206 Partial Content, and advertises `Accept-Ranges: bytes` on every response.

4. **Frontend: single-codec source** — headless Chromium in tests (and Firefox in production) lacks the proprietary H.264 codec. **Fix**: `gen_demos.py` now produces both MP4 (H.264+AAC, Constrained Baseline for max compat) AND WebM (VP9+Opus) for each demo. Frontend `<video>` uses two `<source>` tags — WebM first, MP4 fallback.

### Verified in-browser (Playwright)
- `readyState: 4` (HAVE_ENOUGH_DATA), `duration: 18.008` / `16.008` seconds, `videoWidth: 1280`, `videoHeight: 720`
- Hover triggers `play()`, currentTime advances (showcase at 4.51s = "Any language."; workflow at 6.02s = "03 CAST")
- Backend serves `HTTP 206 Partial Content` with `Content-Range: bytes 0-1023/348011`
- Zero JS console errors, zero video errors

### Files changed
- /app/backend/server.py — `_range_response()`, `_media_type()`, `/storage/{filename}` GET+HEAD
- /app/backend/scripts/gen_demos.py — dual MP4+WebM output, baseline profile, silent audio track
- /app/frontend/src/pages/Landing.jsx — `<source>` fallback (WebM → MP4)

## Update (2026-07-07 · Ramayan-themed demo tile)
### New demo video: "The First Sight · Ramayan"
A 22-second stylized short film themed on Lord Rama's first sight of Sita Mata in Janakpuri, reimagined with copyright-safe original names:
- **Prince Ramaditya** (archetype: noble warrior prince)
- **Princess Vaidehi** (archetype: princess of Mithila)

Three acts, each with English title + Hindi couplet in Devanagari (Lohit-Devanagari font):
- Act I · Arrival in Janakpuri · *जनकपुरी की सुवर्ण भोर*
- Act II · The Royal Garden · *उद्यान में एक पुष्प, एक स्वप्न*
- Act III · The First Glance · *एक क्षण — और संसार ठहर गया*

Closing beats: "An AiPillu original short — A reimagining of the Ramayan — Copyright-safe original characters — Make your own film · aipillu.studio"

### Files
- `/app/backend/scripts/gen_ramayan_styled.py` — ffmpeg-only, no LLM credits (used now)
- `/app/backend/scripts/gen_ramayan_demo.py` — full AI pipeline (Nano Banana + Hindi TTS + Ken-Burns + SRT). Ready to run once Emergent Universal Key balance is topped up (currently exceeded: $1.07/$1.00 budget).
- Warm saffron/gold palette (0xE07A2B + 0xD4AF37), ornate frame borders, drifting vignettes
- Landing page now shows **three demo tiles** in a 3-column grid (Ramayan first for max cultural relevance)

## Note on Emergent LLM Key
- Universal Key budget currently exceeded ($1.07/$1.00). Please top up in Profile → Universal Key → Add Balance to unlock: Nano Banana image generation, OpenAI TTS, Whisper, Claude analyze/translate, Sora 2 video, and the full AI Ramayan demo (`gen_ramayan_demo.py`).

## Bugfix (2026-07-07 · Demo videos playing for ALL end users)
Previously the demo tiles only played on `mouseenter` — which is a desktop-only event. On touch devices (phones, tablets) videos never played and the tile showed a black rectangle with a static gold play button, looking broken.

### Fixes
1. **`autoPlay muted loop playsInline`** on every `<video>` — browser-safe (muted+inline autoplay is universally allowed on iOS Safari, Android Chrome, desktop Firefox/Safari/Edge/Chrome). Videos start playing the instant the page renders, no interaction needed.
2. **Poster JPGs**: extracted at t=2.5s via `ffmpeg -ss 2.5 -frames:v 1 -q:v 3` for every demo (`demo_*_poster.jpg`, ~27-39 KB each). Displayed while the video is still buffering — so users NEVER see a black rectangle.
3. **Removed the hover-dependent state** and the giant central play button. Replaced with a small subtle "TAP FOR SOUND & FULLSCREEN" pill in the bottom-right corner — signals interactivity without covering the content.
4. **Copy update**: "Plays silently on any device — tap for sound and fullscreen" (previously said "autoplays on hover" which was misleading).

### Verified in-browser (Playwright, headless Chromium)
All 3 videos: `readyState: 4`, `currentTime: 4.95s`, `paused: false`, `autoplay: true`, `muted: true`, `error: null`
- Ramayan: 22.01s duration, playing WebM
- Showcase: 18.01s duration, playing WebM
- Workflow: 16.01s duration, playing WebM

Zero JS console errors. Real content visible in every tile without any user interaction.

## Update (2026-07-07 · Traditional names + cinematic Ramayan demo)
### Fixed
1. **Traditional character names restored** — Rama, Sita, Krishna, Shiva, Hanuman etc. are 3000+ year old mythological figures in the public domain. Updated the analyze system prompt (`STORY_SYSTEM_PROMPT` in ai_services.py) to instruct Claude to USE traditional names directly and only reinvent VISUAL DESIGNS to avoid infringing modern film/TV/comic depictions.
2. **New cinematic Ramayan demo** (`gen_ramayan_cinematic.py`):
   - Downloads 3 free-license Pexels images
   - Ken-Burns zoom + drift motion per scene (6.5s each)
   - Warm saffron/gold color grade + vignette + gold border
   - Hindi Devanagari titles + English overlays (Lohit-Devanagari font)
   - Cinematic beat lines top+bottom, English italic subtitles
   - Concatenated with soft SRT via existing `assembly.concat_with_subs`
   - Output: demo_ramayan.mp4 (2.5 MB) + demo_ramayan.webm (4.3 MB) + poster JPG

### Verified in-browser
All 3 tiles autoplaying: Ramayan @ 6.95s (Scene 1 → 2 transition visible), Showcase @ 6.95s, Workflow @ 6.95s ("03 CAST" step). Zero errors.

### Awaiting: Real AI-generated Ramayan
`gen_ramayan_demo.py` runs the full production pipeline (Nano Banana period-authentic character portraits + Hindi TTS + Ken-Burns + soft subs). Blocked ONLY by budget cap on the Emergent Universal Key ($1.07/$1.00). Once topped up:
```
python3 /app/backend/scripts/gen_ramayan_demo.py
```
overwrites the stock-imagery version with a fully AI-generated one.

## Update (2026-07-07 · Real AI-generated Ramayan demo)
### Live on homepage
User topped up Universal Key budget. Ran the full production pipeline:
- **Nano Banana** painted 3 period-authentic scenes (Rama+Lakshman entering Janakpuri; Sita+companions in the royal garden; the first-glance moment)
- **OpenAI TTS onyx** narrated all 3 scenes in Hindi Devanagari
- **Ken-Burns** animated each still, muxed with narration, concatenated with soft SRT
- Output: `demo_ramayan.mp4` (1.9 MB) + `.webm` (3.4 MB) + poster JPG

### Verified in-browser
Playing at t=8.45s showing Sita Mata in emerald sari with companions in Janakpuri garden. Duration 18.09s, `error: null`, `paused: false`.

### Traditional names on-screen
Character names in the narration Hindi: "प्रभु राम" (Lord Rama), "माता सीता" (Mother Sita), "लक्ष्मण" (Lakshmana) — public-domain traditional names. Visual designs are original Nano Banana renderings (period-authentic silks, jewelry, palace architecture) — no infringement of any modern film/TV/comic depiction.


## Update (2026-07-07 · Chandrakanta cartoon demo + per-character voices)

### Feature: Every character speaks in their own voice
Added a universal rule across all films — each character gets a **unique OpenAI TTS voice** from the pool `[onyx, nova, alloy, echo, fable, shimmer, ash, coral, sage]`, and the narrator gets a separate voice.

- `ai_services.STORY_SYSTEM_PROMPT` — extended so Claude assigns:
  - `characters[].voice` — unique per character
  - `scenes[].dialogue_lines` — `[{speaker: "narrator"|char_id, text}, ...]`
  - `narrator_voice` — top-level field
- `ai_services.assign_unique_voices(...)` — post-analyze fallback that repairs any missing/duplicate voices deterministically.
- `ai_services.generate_scene_audio_multivoice(...)` — generates a separate mp3 per dialogue line in each speaker's own voice, then concats with `assembly.concat_audio_files()`.
- `server._analyze_task` now calls `assign_unique_voices` and normalizes `dialogue_lines` on every scene.
- `server.gen_scene_narration`, batch worker, and dub worker all use `generate_scene_audio_multivoice` when dialogue_lines exist, falling back to the legacy single-voice narration otherwise. Multi-voice is applied for **dubs** too — every language track keeps distinct per-character voices.
- `assembly.concat_audio_files(list, out)` — ffmpeg concat-demuxer helper for mp3s.

### New homepage demo: Chandrakanta of Vijaygarh (cartoon)
- Public-domain folk romance (Devaki Nandan Khatri, 1888): Princess Chandrakanta of Vijaygarh + Prince Virendra Singh of Naugarh, aiyar spies, tilism traps.
- Freshly-invented cartoon character designs (flat 2D, folk-poster palette). NOT derived from any prior TV/film/comic adaptation.
- 4 scenes × 3 dialogue lines each = 12 individual TTS clips concat'd per scene.
- 4 distinct voices in the film: **fable** (narrator), **coral** (Chandrakanta), **onyx** (Virendra), **ash** (aiyar Tejsingh).
- Script: `/app/backend/scripts/gen_chandrakanta_demo.py`
- Output: `demo_chandrakanta.mp4` (4.3 MB, 59 s) + `.webm` + `.srt` + `_poster.jpg`.
- Landing page updated to a 4-tile demo grid (Ramayan, Chandrakanta, Showreel, Workflow).

### Verified
- Backend tests: **52 / 52 passing**.
- HTTP Range: `Range: bytes=0-100000` → `206 Partial Content` ✓
- Screenshot: Tile visible, `<video>` reports `readyState=4, duration=59.047, error=null`.

## Backlog / Next
- P1: User to click **"Save to Github"** in the chat input to push the repo (agents cannot perform git writes).
- P2: Optional: batch-render Krishna-Sudama / Hanuman-Ocean / Shiva-Parvati gallery entries using the same multi-voice pipeline.
- P3: Real Instagram/YouTube OAuth uploads (deferred — needs 4-8 week app verification).
- P3: Refactor `Studio.jsx` (~1900 lines) into `/components` folder.


## Update (2026-07-07 · Login required for Studio, Gallery, Downloads & Share)

### Auth architecture
- Two flows on the **same login screen** — user chooses either:
  1. **Continue with Google** → Emergent-managed OAuth. Backend exchanges the one-time `session_id` at `/api/auth/session` → sets `session_token` httpOnly cookie.
  2. **Email + Password** → bcrypt hash + PyJWT `access_token` (7d) + `refresh_token` (30d) httpOnly cookies.
- Unified `get_current_user(request)` accepts EITHER JWT cookie/Bearer OR emergent `session_token`. Both flows write to a single `users` collection keyed by lowercase email; `auth_providers: ["email","google"]` records which methods a user has used.
- Cookies use `Secure=true, SameSite=none, HttpOnly=true, Path=/` so they work across the emergent preview → API domain.

### Gating (via a single FastAPI middleware, `/api/*` scoped)
- **Public**: `/api/health`, `/api/auth/*`, `/api/storage/*` (demo videos, images, TTS previews), `/api/webhook/*`, `/api/voice-preview`.
- **Auth required** (401 for guests): everything else — `/api/projects/*`, `/api/gallery/*`, `/api/tip/*`, `/api/dubs/*`, `/api/checkout/*`, `/api/subtitles/*`.
- **Ownership required** (403 for non-owner, admin bypass): every `/api/projects/{pid}/…` — enforced in the middleware by looking up `owner_email` from the URL-encoded pid.

### Free-tier tied to account (not browser)
- `_user_has_free_tier_used(email)` now counts `projects` where `owner_email == user.email && free_granted == True`. Clearing localStorage no longer resets the free unlock.
- `/claim-free` writes `owner_email` on grant.

### Frontend
- `AuthProvider` context: `{user, isAuthenticated, loading, login, register, logout, loginWithGoogle, exchangeEmergentSession, checkAuth}`.
- `Login` page (`/login`): Google button + email/password toggle + register mode. Full data-testids.
- `AuthCallback` (`/auth/callback`): synchronously reads `#session_id=…`, exchanges it, redirects to `/studio`. Uses `useRef` sentinel to prevent StrictMode double-exchange.
- `ProtectedRoute` wraps Studio + Gallery routes; redirects to `/login` for guests.
- `axios.withCredentials = true` so every API call carries cookies.
- Landing nav gained: **Sign in** button for guests + user badge (avatar/name) + Logout button for authenticated users.

### Data model additions
- `users`: `{user_id, email(unique), name, picture, role, auth_providers[], password_hash(nullable), created_at}`
- `user_sessions`: `{user_id, session_token(unique), email, expires_at(TTL index), source:"emergent"}`
- Existing `projects` docs now include `owner_email` + `owner_user_id` on create.

### Verified
- **Backend tests: 52 / 52 passing** — added an autouse conftest fixture that (a) monkey-patches raw `requests.*` calls to carry admin session cookies, (b) resets admin's free-tier flag between tests.
- E2E frontend smoke: Guest → sees demos + "Sign in" nav ✓. Guest visits `/studio` → redirected to `/login` ✓. Register via email → lands on `/studio` with account-created toast ✓. New user starts with empty project list (owner-scoped filter) ✓.
- Chandrakanta demo (and all `/api/storage/demo_*`) remains public — guest can watch without logging in.

### Test credentials
Written to `/app/memory/test_credentials.md`:
- Admin: `admin@aipillu.studio` / `aipilluAdmin@2026`

## Backlog / Next
- P1: User to click **"Save to Github"** in the chat input to push the repo.
- P2: **Voice cast panel** in Studio letting users override each character's voice with a preview button.
- P2 (optional): Batch-render Krishna-Sudama / Hanuman-Ocean / Shiva-Parvati gallery entries using the multi-voice pipeline.
- P3: Password reset ("forgot password") — the JWT playbook covers it but wasn't yet wired.
- P3: Real Instagram/YouTube OAuth uploads (deferred — needs 4-8 week app verification).
- P3: Refactor `Studio.jsx` (~1900 lines) into a `/components` folder.
