#!/usr/bin/env python3
"""Fast, deterministic branded demo MP4 generator for the AiPillu landing page.
Uses only lavfi color + drawtext + drawbox — no per-pixel `geq` (which is slow).
Run: python3 /app/backend/scripts/gen_demos.py
Outputs:
  /app/backend/storage/demo_showcase.mp4
  /app/backend/storage/demo_workflow.mp4
"""
import os
import subprocess
from pathlib import Path

STORAGE = Path(os.getenv("STORAGE_DIR", "/app/backend/storage"))
STORAGE.mkdir(parents=True, exist_ok=True)

FONT_SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
FONT_SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_ITALIC = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"

GOLD = "0xD4AF37"
BLACK = "0x0A0A0A"

W, H = 1280, 720
FPS = 30


def run(cmd):
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if proc.returncode != 0:
        print("FFMPEG ERROR:", proc.stderr[-1500:])
        raise SystemExit(1)


def esc(t):
    return t.replace("\\", "\\\\").replace(":", r"\:").replace("'", "\u2019").replace(",", r"\,")


def build_showcase():
    """~18s trailer with typographic beats over a black canvas with a slowly-drifting gold rectangle."""
    out = STORAGE / "demo_showcase.mp4"

    beats = [
        (0.5, 3.5, "Every story",              80, -60, FONT_SERIF, "white"),
        (0.9, 3.9, "deserves a screen.",       60, 30,  FONT_ITALIC, "#D4AF37"),

        (4.0, 6.8, "Any language.",            72, -20, FONT_SERIF,  "white"),
        (4.4, 6.8, "Hindi   English   Arabic   Mandarin   Tamil   Swahili   \u2026", 22, 45, FONT_SANS, "#D4AF37"),

        (7.0, 10.0, "Any source.",             72, -60, FONT_SERIF,  "white"),
        (7.4, 10.0, "PDF   Script   Voice   URL",  26, 30, FONT_SANS, "#D4AF37"),

        (10.2, 13.2, "Original characters.",   72, -20, FONT_SERIF,  "white"),
        (10.6, 13.2, "Copyright-safe by design.", 24, 40, FONT_SANS, "#D4AF37"),

        (13.4, 17.5, "AiPillu Studio",         92, -20, FONT_BOLD,   "white"),
        (13.9, 17.5, "Story to Film - one click", 26, 55, FONT_SANS, "#D4AF37"),
    ]

    fx = []
    # Decorative moving gold vignette (a drawbox with alpha)
    # Two soft rectangles that drift for subtle motion
    fx.append("drawbox=x='(w/4)+sin(t/2)*80':y='(h/4)+cos(t/2)*40':w=600:h=340:color=0xD4AF37@0.06:t=fill")
    fx.append("drawbox=x='(w/2)+sin(t/3+1)*100':y='(h/3)+cos(t/3)*60':w=520:h=300:color=0xD4AF37@0.04:t=fill")
    # Subtle bottom bar
    fx.append(f"drawbox=x=0:y=h-4:w={W}:h=4:color=0xD4AF37@0.6:t=fill")
    # Top-left tiny gold square (branding accent)
    fx.append("drawbox=x=64:y=56:w=8:h=8:color=0xD4AF37@0.9:t=fill")
    # Small "SHOWCASE" tag top-left
    fx.append(f"drawtext=fontfile={FONT_SANS}:text='AIPILLU  \u2022  SHOWREEL':fontcolor=0xD4AF37@0.75:fontsize=13:x=84:y=54")

    for s, e, text, size, y_off, font, color in beats:
        t = esc(text)
        alpha_expr = f"if(lt(t,{s}+0.4),(t-{s})/0.4,if(gt(t,{e}-0.5),(({e}-t)/0.5),1))"
        y_expr = f"(h-text_h)/2+{y_off}"
        fx.append(
            f"drawtext=fontfile={font}:text='{t}':fontcolor={color}:fontsize={size}"
            f":x=(w-text_w)/2:y={y_expr}"
            f":alpha='if(between(t,{s},{e}),{alpha_expr},0)'"
        )

    filter_chain = ",".join(fx) + ",format=yuv420p"
    bg = f"color=c={BLACK}:s={W}x{H}:d=18:r={FPS}"
    # Add a silent audio track for maximum browser compatibility (some browsers reject video-only MP4)
    cmd = (
        f'ffmpeg -y '
        f'-f lavfi -i "{bg}" '
        f'-f lavfi -i "anullsrc=channel_layout=stereo:sample_rate=44100" '
        f'-vf "{filter_chain}" '
        f'-t 18 '
        f'-c:v libx264 -profile:v baseline -level 3.0 -pix_fmt yuv420p -preset veryfast -crf 22 '
        f'-c:a aac -b:a 96k -shortest '
        f'-movflags +faststart '
        f'"{out}"'
    )
    run(cmd)
    # Also produce a WebM (VP9 + Opus) fallback for Chromium-based browsers without H.264
    out_webm = str(out).replace(".mp4", ".webm")
    cmd_webm = (
        f'ffmpeg -y '
        f'-f lavfi -i "{bg}" '
        f'-f lavfi -i "anullsrc=channel_layout=stereo:sample_rate=48000" '
        f'-vf "{filter_chain}" '
        f'-t 18 '
        f'-c:v libvpx-vp9 -b:v 0 -crf 32 -deadline realtime -cpu-used 8 '
        f'-c:a libopus -b:a 64k -shortest '
        f'"{out_webm}"'
    )
    run(cmd_webm)
    print(f"OK: {out}  ({out.stat().st_size/1024:.0f} KB)")
    print(f"OK: {out_webm}  ({os.path.getsize(out_webm)/1024:.0f} KB)")


def build_workflow():
    """~16s workflow strip: six numbered steps fade through, with a shared footer."""
    out = STORAGE / "demo_workflow.mp4"

    steps = [
        ("01", "INGEST",   "Drop a PDF, paste a script, or record your voice."),
        ("02", "ANALYZE",  "Claude drafts characters, scenes, camera language."),
        ("03", "CAST",     "Nano Banana paints original, copyright-safe characters."),
        ("04", "ANIMATE",  "Sora 2 or Ken-Burns brings every frame to life."),
        ("05", "NARRATE",  "OpenAI TTS in 100+ world languages."),
        ("06", "SHARE",    "Download MP4 with SRT subs, publish, get tipped."),
    ]

    per = 2.5
    total = per * len(steps) + 1

    fx = []
    # Gold accents
    fx.append(f"drawbox=x=0:y=h-4:w={W}:h=4:color=0xD4AF37@0.6:t=fill")
    fx.append("drawbox=x=64:y=56:w=8:h=8:color=0xD4AF37@0.9:t=fill")
    fx.append(f"drawtext=fontfile={FONT_SANS}:text='AIPILLU  \u2022  WORKFLOW':fontcolor=0xD4AF37@0.75:fontsize=13:x=84:y=54")

    for i, (num, label, desc) in enumerate(steps):
        s = 0.4 + i * per
        e = s + per - 0.15
        alpha_in = f"if(lt(t,{s}+0.4),(t-{s})/0.4,if(gt(t,{e}-0.35),(({e}-t)/0.35),1))"

        fx.append(
            f"drawtext=fontfile={FONT_BOLD}:text='{esc(num)}':fontcolor=0xD4AF37:fontsize=180"
            f":x=110:y=(h-text_h)/2-30"
            f":alpha='if(between(t,{s},{e}),{alpha_in},0)'"
        )
        fx.append(
            f"drawtext=fontfile={FONT_BOLD}:text='{esc(label)}':fontcolor=white:fontsize=64"
            f":x=360:y=(h-text_h)/2-30"
            f":alpha='if(between(t,{s},{e}),{alpha_in},0)'"
        )
        fx.append(
            f"drawtext=fontfile={FONT_SANS}:text='{esc(desc)}':fontcolor=0xD0D0D0:fontsize=26"
            f":x=360:y=(h-text_h)/2+40"
            f":alpha='if(between(t,{s},{e}),{alpha_in},0)'"
        )

    fx.append(
        f"drawtext=fontfile={FONT_SANS}:text='AiPillu Studio  \u2022  aipillu.studio':"
        f"fontcolor=0xD4AF37:fontsize=20:x=(w-text_w)/2:y=h-46"
    )

    filter_chain = ",".join(fx) + ",format=yuv420p"
    bg = f"color=c={BLACK}:s={W}x{H}:d={total}:r={FPS}"
    cmd = (
        f'ffmpeg -y '
        f'-f lavfi -i "{bg}" '
        f'-f lavfi -i "anullsrc=channel_layout=stereo:sample_rate=44100" '
        f'-vf "{filter_chain}" '
        f'-t {total} '
        f'-c:v libx264 -profile:v baseline -level 3.0 -pix_fmt yuv420p -preset veryfast -crf 22 '
        f'-c:a aac -b:a 96k -shortest '
        f'-movflags +faststart '
        f'"{out}"'
    )
    run(cmd)
    # WebM fallback
    out_webm = str(out).replace(".mp4", ".webm")
    cmd_webm = (
        f'ffmpeg -y '
        f'-f lavfi -i "{bg}" '
        f'-f lavfi -i "anullsrc=channel_layout=stereo:sample_rate=48000" '
        f'-vf "{filter_chain}" '
        f'-t {total} '
        f'-c:v libvpx-vp9 -b:v 0 -crf 32 -deadline realtime -cpu-used 8 '
        f'-c:a libopus -b:a 64k -shortest '
        f'"{out_webm}"'
    )
    run(cmd_webm)
    print(f"OK: {out}  ({out.stat().st_size/1024:.0f} KB)")
    print(f"OK: {out_webm}  ({os.path.getsize(out_webm)/1024:.0f} KB)")


if __name__ == "__main__":
    build_showcase()
    build_workflow()
    print("\nAll demo videos generated in", STORAGE)
