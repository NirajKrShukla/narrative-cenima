#!/usr/bin/env python3
"""Generate the AiPillu 'Chandrakanta of Vijaygarh' cartoon demo film.

Story beats (public-domain folk-romance by Devaki Nandan Khatri, 1888):
  Princess Chandrakanta of Vijaygarh and Prince Virendra Singh of Naugarh
  are in love. Aiyars (secret spies) carry their messages across enemy lines,
  and their path is riddled with tilism — enchanted mechanical traps.

Visual style: **flat 2D cartoon** — freshly invented character designs, NOT
resembling any known TV/film/comic version. Warm folk-poster palette (jewel
tones on parchment) with soft cel-shading. Copyright-safe.

Every character has their OWN OpenAI TTS voice — narrator (fable), the
princess (coral), the prince (onyx), a wily aiyar spy (ash).

Output:
  /app/backend/storage/demo_chandrakanta.mp4  (+ .webm, .srt, _poster.jpg)
"""
from __future__ import annotations
import asyncio
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "/app/backend")

from dotenv import load_dotenv
load_dotenv("/app/backend/.env")

import ai_services  # noqa: E402
import assembly     # noqa: E402

STORAGE = Path(os.getenv("STORAGE_DIR", "/app/backend/storage"))
PID = "demo_chandrakanta"

# --- Design DNA -------------------------------------------------------------
# All names, silhouettes and props are original inventions — NOT derived from
# any prior TV, film, or comic adaptation of Chandrakanta.
CARTOON_STYLE = (
    "flat 2D cartoon illustration, thick clean outlines, warm folk-poster palette "
    "of saffron, peacock-teal, magenta and old-parchment cream, soft cel-shading, "
    "hand-drawn texture on gently grainy paper, whimsical and cinematic, no photorealism, "
    "no watermarks, no text overlays"
)

# Character descriptions — used inline in image prompts for consistency.
CHAR_CHANDRAKANTA = (
    "PRINCESS CHANDRAKANTA of Vijaygarh — a doe-eyed young cartoon princess with "
    "long jet-black wavy hair tied with jasmine, warm caramel skin, wearing a "
    "flowing peacock-teal ghagra-choli embroidered with tiny gold moons, a "
    "single crescent-moon nose ring and silver anklets. Round expressive eyes, "
    "gentle heart-shaped face, a small mole on her left cheek"
)
CHAR_VIRENDRA = (
    "PRINCE VIRENDRA SINGH of Naugarh — a brave young cartoon prince with dark "
    "swept-back hair, sharp angular jaw, thin moustache, warm bronze skin. He wears "
    "a fitted crimson bandhgala achkan with saffron sash, cream churidar and a "
    "tiny silver sword at his hip. A bold sun-emblem medallion on his chest"
)
CHAR_AIYAR = (
    "TEJSINGH the AIYAR — a wiry cartoon shape-shifting spy with mischievous grin, "
    "bright green domino mask, a wide-brimmed straw traveller's hat, patched "
    "olive-and-mustard tunic, a hollow bamboo flute (secret dart pipe) slung across "
    "his back, and a leather scroll-pouch at his belt"
)

SCENES = [
    {
        "id": "sc1",
        "title": "Two Kingdoms, One Heart",
        "image_prompt": (
            f"Split cartoon panel showing two neighbouring kingdoms across a moonlit river. "
            f"Left: {CHAR_CHANDRAKANTA}, standing on the marble balcony of Vijaygarh palace, "
            f"gazing at the stars, holding a lotus. Right: {CHAR_VIRENDRA}, on the rampart of "
            f"Naugarh fort, holding a paper scroll to his heart. A single fluttering white dove "
            f"flies between them across the sky. Warm folk-poster palette, gentle romance, "
            f"tiny hearts drifting on the wind"
        ),
        "dialogues": [
            {"speaker": "narrator", "text":
                "Between two kingdoms — Vijaygarh and Naugarh — lived a love that no border could contain."},
            {"speaker": "chandrakanta", "text":
                "Every star tonight reminds me of him… my Virendra."},
            {"speaker": "virendra", "text":
                "One day, Chandrakanta — I shall cross a hundred obstacles to reach you."},
        ],
    },
    {
        "id": "sc2",
        "title": "The Aiyar's Message",
        "image_prompt": (
            f"Cartoon interior of a torch-lit palace corridor at night. {CHAR_AIYAR}, "
            f"crouched behind a lion-carved pillar, hands a rolled parchment tied with a "
            f"red silk thread to {CHAR_CHANDRAKANTA}, who receives it with wide hopeful eyes. "
            f"A single oil lamp flickers, casting long shadows. Playful mysterious mood, "
            f"secret rendezvous, faint sparkles around the scroll"
        ),
        "dialogues": [
            {"speaker": "aiyar", "text":
                "Princess — a scroll for you, sealed in Naugarh red. My tongue is quicker than a sparrow, my feet quicker still."},
            {"speaker": "chandrakanta", "text":
                "Bless you, Tejsingh. Tell my prince I read every word twice… and dream them a third time."},
            {"speaker": "narrator", "text":
                "The aiyars — masters of disguise — carried love and secrets across enemy walls."},
        ],
    },
    {
        "id": "sc3",
        "title": "The Tilism of Traps",
        "image_prompt": (
            f"Cartoon wide shot of an enchanted mechanical jungle at dusk. {CHAR_VIRENDRA} "
            f"leaps mid-air across shifting stone tiles that bloom into spinning brass blades. "
            f"Giant clockwork peacocks with sapphire tail-fans block his path, glowing runes "
            f"pulse on ancient temple walls behind him. Swirling green magical dust, thrilling "
            f"action pose, dynamic diagonal composition, folk-poster palette"
        ),
        "dialogues": [
            {"speaker": "narrator", "text":
                "The path was a tilism — an enchantment of shifting stones, dart-flowers and clockwork guardians."},
            {"speaker": "virendra", "text":
                "For Chandrakanta — I shall bend even magic to my will!"},
            {"speaker": "aiyar", "text":
                "This way, prince! The mechanical peacock strikes on every third breath — count carefully!"},
        ],
    },
    {
        "id": "sc4",
        "title": "The Reunion",
        "image_prompt": (
            f"Cartoon soft-lit garden pavilion at sunrise. {CHAR_VIRENDRA} and "
            f"{CHAR_CHANDRAKANTA} finally meet — hands clasped, foreheads almost touching, "
            f"surrounded by cascading jasmine and marigold petals. A rainbow arcs behind "
            f"the pavilion, dawn light streams golden. {CHAR_AIYAR} peeks from behind a "
            f"pillar with a wide happy grin and a thumbs-up. Warm romantic close-up, "
            f"gentle bokeh, folk-poster palette"
        ),
        "dialogues": [
            {"speaker": "chandrakanta", "text":
                "You truly came. Through fire, through magic, through fear…"},
            {"speaker": "virendra", "text":
                "For you, I would cross a thousand tilisms — and a thousand more."},
            {"speaker": "narrator", "text":
                "And so love — braver than any spy and older than any enchantment — wrote its own ending."},
        ],
    },
]

# Character -> voice mapping (each character has a UNIQUE OpenAI TTS voice)
CHARACTERS = [
    {"id": "chandrakanta", "voice": "coral"},   # warm feminine
    {"id": "virendra",     "voice": "onyx"},    # deep heroic male
    {"id": "aiyar",        "voice": "ash"},     # warm mature male, playful
]
NARRATOR_VOICE = "fable"                        # British storyteller narrator


async def gen_image(scene: dict) -> str:
    fname = f"{PID}_{scene['id']}.png"
    prompt = f"{scene['image_prompt']}. Style: {CARTOON_STYLE}."
    print(f"  [image] {scene['id']} — Nano Banana rendering cartoon…")
    await ai_services.generate_image(prompt, fname)
    return fname


async def gen_multivoice_audio(scene: dict) -> str:
    fname = f"{PID}_{scene['id']}.mp3"
    print(f"  [tts]   {scene['id']} — multi-voice ({len(scene['dialogues'])} lines)…")
    await ai_services.generate_scene_audio_multivoice(
        scene["dialogues"], CHARACTERS, NARRATOR_VOICE, fname, model="tts-1",
    )
    return fname


def to_webm(mp4_path: Path) -> None:
    webm = mp4_path.with_suffix(".webm")
    cmd = (
        f'ffmpeg -y -i "{mp4_path}" '
        f'-c:v libvpx-vp9 -b:v 0 -crf 34 -deadline realtime -cpu-used 8 '
        f'-c:a libopus -b:a 64k "{webm}"'
    )
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if proc.returncode != 0:
        print("webm err:", proc.stderr[-800:])
    else:
        print(f"  [webm] {webm.name}  ({webm.stat().st_size/1024:.0f} KB)")


def make_poster(image_file: str, out_name: str) -> None:
    src = STORAGE / image_file
    dst = STORAGE / out_name
    cmd = ["ffmpeg", "-y", "-i", str(src), "-vf", "scale=1280:720", "-q:v", "3", str(dst)]
    subprocess.run(cmd, capture_output=True)


async def main() -> None:
    STORAGE.mkdir(parents=True, exist_ok=True)
    print(f">>> Generating Chandrakanta cartoon demo ({len(SCENES)} scenes, {len(CHARACTERS)}+narrator voices)")

    per_scene_files: list[str] = []
    per_scene_narr: list[str] = []
    first_img = None

    for s in SCENES:
        img = await gen_image(s)
        if not first_img:
            first_img = img
        # Match scene duration to audio duration (with a small tail)
        audio = await gen_multivoice_audio(s)
        audio_dur = assembly.probe_duration(audio) or 6.0
        scene_dur = max(6, int(round(audio_dur + 0.6)))

        kb_file = f"{PID}_{s['id']}_kb.mp4"
        assembly.image_to_video(img, kb_file, duration=scene_dur, size="1280x720")

        mux_file = f"{PID}_{s['id']}_final.mp4"
        assembly.mux_scene(kb_file, audio, mux_file, None)
        per_scene_files.append(mux_file)
        # SRT: join all dialogue text lines together for readability
        per_scene_narr.append(" ".join(ln["text"] for ln in s["dialogues"]))
        print(f"  [scene] {s['id']} ready ({scene_dur}s)")

    print(">>> Concatenating with soft subtitles…")
    final_mp4 = f"{PID}.mp4"
    final_srt = f"{PID}.srt"
    assembly.concat_with_subs(per_scene_files, per_scene_narr, final_mp4, final_srt)
    mp4_path = STORAGE / final_mp4
    print(f"  [final] {mp4_path.name}  ({mp4_path.stat().st_size/1024:.0f} KB)")

    print(">>> Encoding WebM fallback…")
    to_webm(mp4_path)

    if first_img:
        make_poster(first_img, f"{PID}_poster.jpg")
        print(f"  [poster] {PID}_poster.jpg")

    print("\n✅ Chandrakanta cartoon demo generated.\n")


if __name__ == "__main__":
    asyncio.run(main())
