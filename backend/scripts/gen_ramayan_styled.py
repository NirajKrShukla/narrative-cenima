#!/usr/bin/env python3
"""Stylized Ramayan-themed demo video for the AiPillu landing page.
Uses ffmpeg + drawtext only (no AI credits). When the Emergent LLM key has
budget again, run `gen_ramayan_demo.py` instead for a real AI-generated version.

Theme: The First Sight — Prince Ramaditya beholds Princess Vaidehi in Janakpuri.
"""
import os
import subprocess
from pathlib import Path

STORAGE = Path(os.getenv("STORAGE_DIR", "/app/backend/storage"))

FONT_SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
FONT_SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_ITALIC = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"

# A serif Devanagari font that handles Hindi text well.
FONT_HINDI = None
for path in [
    "/usr/share/fonts/truetype/lohit-devanagari/Lohit-Devanagari.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/truetype/samyak/Samyak-Devanagari.ttf",
]:
    if os.path.exists(path):
        FONT_HINDI = path
        break

W, H = 1280, 720
FPS = 30
DUR = 22  # ~22 seconds total

# Warm saffron/gold palette for the Ramayan aesthetic
BG = "0x0A0705"      # deep charcoal with warm undertone
SAFFRON = "0xE07A2B"
GOLD = "0xD4AF37"
CREAM = "0xF3E4C3"


def run(cmd):
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if proc.returncode != 0:
        print("FFMPEG ERROR:", proc.stderr[-1500:])
        raise SystemExit(1)


def esc(t):
    return t.replace("\\", "\\\\").replace(":", r"\:").replace("'", "\u2019").replace(",", r"\,")


def build():
    out = STORAGE / "demo_ramayan.mp4"

    # Story beats — English + Hindi couplet per act
    beats = [
        # (start, end, text, size, y_off, font, color)
        # Act I – Arrival
        (0.6, 4.5, "ACT   I",                                  30, -220, FONT_SANS, GOLD),
        (0.9, 4.5, "Arrival in Janakpuri",                     72,  -120, FONT_SERIF, CREAM),
        (1.4, 4.5, "Prince Ramaditya rides at dawn",           26,  -30, FONT_ITALIC, GOLD),
        (1.8, 4.5, "जनकपुरी की सुवर्ण भोर",                       36,  50, FONT_HINDI or FONT_SERIF, CREAM),

        # Act II – The Garden
        (5.0, 9.0, "ACT   II",                                 30, -220, FONT_SANS, GOLD),
        (5.3, 9.0, "The Royal Garden",                         72, -120, FONT_SERIF, CREAM),
        (5.8, 9.0, "Princess Vaidehi gathers jasmine",         26,  -30, FONT_ITALIC, GOLD),
        (6.2, 9.0, "उद्यान में एक पुष्प, एक स्वप्न",                 36,  50, FONT_HINDI or FONT_SERIF, CREAM),

        # Act III – The First Glance
        (9.5, 14.0, "ACT   III",                               30, -220, FONT_SANS, GOLD),
        (9.8, 14.0, "The First Glance",                        72, -120, FONT_SERIF, CREAM),
        (10.3, 14.0, "Two eyes meet — the world stills",       26,  -30, FONT_ITALIC, GOLD),
        (10.7, 14.0, "एक क्षण — और संसार ठहर गया",              36,  50, FONT_HINDI or FONT_SERIF, CREAM),

        # Closing — the poem
        (14.5, 19.0, "\u2014 An AiPillu original short \u2014", 22, -180, FONT_ITALIC, GOLD),
        (14.9, 19.0, "The First Sight",                        90,  -80, FONT_SERIF, CREAM),
        (15.5, 19.0, "A reimagining of the Ramayan",           24,   20, FONT_SANS, GOLD),
        (16.0, 19.0, "Copyright-safe original characters",     18,   60, FONT_SANS, GOLD),

        # AiPillu tag
        (19.5, 21.9, "Make your own film",                     42,  -30, FONT_BOLD, CREAM),
        (19.9, 21.9, "aipillu.studio",                         22,   30, FONT_SANS, GOLD),
    ]

    fx = []
    # Ornamental frame — warm saffron border strips
    fx.append(f"drawbox=x=0:y=0:w={W}:h=6:color={SAFFRON}@0.85:t=fill")
    fx.append(f"drawbox=x=0:y={H-6}:w={W}:h=6:color={SAFFRON}@0.85:t=fill")
    fx.append(f"drawbox=x=0:y=6:w=6:h={H-12}:color={GOLD}@0.6:t=fill")
    fx.append(f"drawbox=x={W-6}:y=6:w=6:h={H-12}:color={GOLD}@0.6:t=fill")
    # Soft warm vignette (two slowly drifting saffron rectangles)
    fx.append(f"drawbox=x='(w/4)+sin(t/2)*90':y='(h/4)+cos(t/2)*45':w=620:h=360:color={SAFFRON}@0.06:t=fill")
    fx.append(f"drawbox=x='(w/2)+cos(t/3)*100':y='(h/3)+sin(t/3)*60':w=520:h=320:color={GOLD}@0.05:t=fill")
    # Top-left branding
    fx.append(f"drawbox=x=64:y=52:w=8:h=8:color={GOLD}@0.9:t=fill")
    fx.append(f"drawtext=fontfile={FONT_SANS}:text='AIPILLU  \u2022  RAMAYAN SHORT':fontcolor={GOLD}@0.85:fontsize=13:x=84:y=50")

    for s, e, text, size, y_off, font, color in beats:
        t = esc(text)
        alpha_expr = f"if(lt(t,{s}+0.5),(t-{s})/0.5,if(gt(t,{e}-0.6),(({e}-t)/0.6),1))"
        y_expr = f"(h-text_h)/2+{y_off}"
        fx.append(
            f"drawtext=fontfile={font}:text='{t}':fontcolor={color}:fontsize={size}"
            f":x=(w-text_w)/2:y={y_expr}"
            f":alpha='if(between(t,{s},{e}),{alpha_expr},0)'"
        )

    filter_chain = ",".join(fx) + ",format=yuv420p"
    bg = f"color=c={BG}:s={W}x{H}:d={DUR}:r={FPS}"

    # MP4 (H.264 Constrained Baseline + AAC + silent audio track for max compatibility)
    cmd_mp4 = (
        f'ffmpeg -y '
        f'-f lavfi -i "{bg}" '
        f'-f lavfi -i "anullsrc=channel_layout=stereo:sample_rate=44100" '
        f'-vf "{filter_chain}" '
        f'-t {DUR} '
        f'-c:v libx264 -profile:v baseline -level 3.0 -pix_fmt yuv420p -preset veryfast -crf 22 '
        f'-c:a aac -b:a 96k -shortest -movflags +faststart '
        f'"{out}"'
    )
    run(cmd_mp4)
    print(f"OK: {out}  ({out.stat().st_size/1024:.0f} KB)")

    # WebM (VP9 + Opus) fallback for Chromium/Firefox
    out_webm = out.with_suffix(".webm")
    cmd_webm = (
        f'ffmpeg -y '
        f'-f lavfi -i "{bg}" '
        f'-f lavfi -i "anullsrc=channel_layout=stereo:sample_rate=48000" '
        f'-vf "{filter_chain}" '
        f'-t {DUR} '
        f'-c:v libvpx-vp9 -b:v 0 -crf 32 -deadline realtime -cpu-used 8 '
        f'-c:a libopus -b:a 64k -shortest '
        f'"{out_webm}"'
    )
    run(cmd_webm)
    print(f"OK: {out_webm}  ({out_webm.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    if FONT_HINDI is None:
        print("Note: No Devanagari font found; Hindi lines will fall back to Latin serif.")
    build()
    print("\nRamayan demo generated.")
