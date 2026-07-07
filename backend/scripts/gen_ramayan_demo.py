#!/usr/bin/env python3
"""Generate a real Ramayan-themed demo film for the AiPillu landing page.

Theme: The First Sight — Prince Ramaditya beholds Princess Vaidehi in the gardens
of Janakpuri (a copyright-safe reimagining of the classic Ramayan scene).

Uses the actual production pipeline (Nano Banana images + Hindi TTS + Ken-Burns +
soft subtitles), so this doubles as an integration sanity check.

Output:
  /app/backend/storage/demo_ramayan.mp4
  /app/backend/storage/demo_ramayan.webm
  /app/backend/storage/demo_ramayan.srt
"""
import asyncio
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Make backend imports resolvable
sys.path.insert(0, "/app/backend")

from dotenv import load_dotenv
load_dotenv("/app/backend/.env")

import ai_services  # noqa: E402
import assembly     # noqa: E402

STORAGE = Path(os.getenv("STORAGE_DIR", "/app/backend/storage"))
PID = "demo_ramayan"

# ---- The 3-scene blueprint (hand-crafted for cinematic pacing) ----
VISUAL_STYLE = (
    "Ornate ancient Indian epic cinema, warm golden hour light, rich saffron and "
    "royal blue palette, painterly 35mm film grain, wide symmetrical composition"
)

# Copyright-safe original names, inspired by the archetypes but distinctly new.
SCENES = [
    {
        "id": "sc1",
        "title": "Arrival in Janakpuri",
        "narration": "जनकपुरी की सुबह — राजकुमार रामादित्य अपने भाई के साथ नगर की ओर बढ़ते हैं, हवा में पुष्पों की सुगंध और शहनाइयों की मधुर ध्वनि।",
        "image_prompt": (
            "Original epic Indian prince Ramaditya, a noble young warrior with dark flowing hair, "
            "adorned in cream-and-gold dhoti with turquoise cape and jeweled crown, walking beside "
            "his younger brother through the gilded gates of a mythical city Janakpuri at dawn. "
            "Ornate stone archways covered in marigold garlands, silk banners in saffron and blue, "
            "temple spires in the distance, warm golden sunrise light, cinematic wide shot, "
            "painterly 35mm film grain, ultra detailed. No text or watermarks."
        ),
    },
    {
        "id": "sc2",
        "title": "The Royal Garden",
        "narration": "उद्यान के मध्य, राजकुमारी वैदेही अपनी सखियों संग पुष्प चुन रही थीं — मानो सूर्य स्वयं धरती पर उतर आया हो।",
        "image_prompt": (
            "Original princess Vaidehi standing amid a lush palace garden at golden hour — a serene "
            "young woman with long dark hair wearing an emerald-and-gold silk sari, delicate gold "
            "jewelry and a lotus in her hair. Surrounded by three companions in pastel saris, gently "
            "gathering jasmine and hibiscus flowers. Marble pavilions, lily ponds with peacocks, "
            "banyan trees, soft warm sunset light. Cinematic three-quarter shot, painterly 35mm, "
            "ornate epic Indian cinema. No text, no watermarks."
        ),
    },
    {
        "id": "sc3",
        "title": "The First Glance",
        "narration": "दो नयनों ने दो नयनों को देखा — और उस एक क्षण में, संसार ठहर गया। यही थी पहली भेंट।",
        "image_prompt": (
            "Close cinematic shot: Prince Ramaditya glances up through the garden trellis, and "
            "Princess Vaidehi turns at that very instant — their eyes meet across a stream of falling "
            "flower petals, warm golden bokeh, soft focus background. Both figures partially framed "
            "by carved stone lattice windows. Time-suspended romantic epic moment, painterly 35mm, "
            "extraordinarily beautiful lighting, saffron and rose-gold palette. No text, no watermarks."
        ),
    },
]


async def gen_image(scene):
    print(f"  [image] {scene['id']} — Nano Banana rendering…")
    fname = f"{PID}_{scene['id']}.png"
    prompt = f"{scene['image_prompt']} Style: {VISUAL_STYLE}."
    await ai_services.generate_image(prompt, fname)
    return fname


async def gen_audio(scene):
    print(f"  [tts]   {scene['id']} — Hindi narration…")
    fname = f"{PID}_{scene['id']}.mp3"
    await ai_services.generate_narration(
        scene["narration"], fname, voice="onyx", model="tts-1"
    )
    return fname


def kb(image_file, out_name):
    return assembly.image_to_video(image_file, out_name, duration=6, size="1280x720")


def to_webm(mp4_path: Path):
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


async def main():
    STORAGE.mkdir(parents=True, exist_ok=True)
    print(f">>> Generating Ramayan demo film ({len(SCENES)} scenes)")

    per_scene_files = []
    per_scene_narr = []
    for s in SCENES:
        img = await gen_image(s)
        audio = await gen_audio(s)
        kb_file = f"{PID}_{s['id']}_kb.mp4"
        assembly.image_to_video(img, kb_file, duration=6, size="1280x720")
        # Mux Ken-Burns video with narration audio (no burned-in text; subtitles come via SRT)
        mux_file = f"{PID}_{s['id']}_final.mp4"
        assembly.mux_scene(kb_file, audio, mux_file, None)
        per_scene_files.append(mux_file)
        per_scene_narr.append(s["narration"])
        print(f"  [scene] {s['id']} ready ({mux_file})")

    # Concatenate with soft subtitles
    print(">>> Concatenating with soft subtitles…")
    final_mp4 = f"{PID}.mp4"
    final_srt = f"{PID}.srt"
    assembly.concat_with_subs(per_scene_files, per_scene_narr, final_mp4, final_srt)
    mp4_path = STORAGE / final_mp4
    print(f"  [final] {mp4_path.name}  ({mp4_path.stat().st_size/1024:.0f} KB)")

    # Also produce a WebM for Chromium/Firefox fallback on the landing page
    print(">>> Encoding WebM fallback…")
    to_webm(mp4_path)
    print("\n✅ Ramayan demo generated.\n")


if __name__ == "__main__":
    asyncio.run(main())
