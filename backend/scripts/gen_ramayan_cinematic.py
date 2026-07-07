#!/usr/bin/env python3
"""Cinematic Ramayan demo using free Unsplash stock imagery + Ken-Burns motion.
Traditional names (Rama, Sita) — 3000+ year old mythological figures in the
public domain. Visual designs come from period-authentic historical photography,
not any copyrighted film/TV depiction.

Scene: The First Sight — Lord Rama beholds Sita Mata in the royal garden of Janakpuri.

Output:
  /app/backend/storage/demo_ramayan.mp4
  /app/backend/storage/demo_ramayan.webm
  /app/backend/storage/demo_ramayan.srt
"""
import os
import subprocess
import sys
from pathlib import Path

import httpx

sys.path.insert(0, "/app/backend")
import assembly  # noqa: E402

STORAGE = Path(os.getenv("STORAGE_DIR", "/app/backend/storage"))

FONT_SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
FONT_SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_ITALIC = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"
FONT_HINDI = "/usr/share/fonts/truetype/lohit-devanagari/Lohit-Devanagari.ttf"

# Three cinematic Unsplash images — Indian temple / palace / garden aesthetic.
# Unsplash license: free for commercial use, no attribution required.
SCENES = [
    {
        "id": "sc1",
        "img_url": "https://images.pexels.com/photos/18415806/pexels-photo-18415806.jpeg?auto=compress&cs=tinysrgb&w=1600",
        "title_en": "Arrival in Janakpuri",
        "title_hi": "जनकपुरी में प्रवेश",
        "beat_en": "Lord Rama enters the kingdom at dawn.",
        "beat_hi": "प्रभु राम प्रातःकाल नगर में पधारते हैं।",
        "narration": "जनकपुरी की सुवर्ण भोर में, प्रभु राम अपने भाई लक्ष्मण के साथ नगर की ओर बढ़ते हैं — पुष्पों की सुगंध और शहनाइयों की मधुर ध्वनि से भरा हुआ वातावरण।",
    },
    {
        "id": "sc2",
        "img_url": "https://images.pexels.com/photos/1051075/pexels-photo-1051075.jpeg?auto=compress&cs=tinysrgb&w=1600",
        "title_en": "The Royal Garden",
        "title_hi": "राजोद्यान का सौंदर्य",
        "beat_en": "Sita Mata gathers flowers with her friends.",
        "beat_hi": "सीता माता अपनी सखियों संग पुष्प चुनती हैं।",
        "narration": "उद्यान के मध्य, माता सीता अपनी सखियों संग जासमीन के फूल एकत्रित कर रही थीं — जैसे सूर्य स्वयं धरती पर उतर आया हो।",
    },
    {
        "id": "sc3",
        "img_url": "https://images.pexels.com/photos/2098405/pexels-photo-2098405.jpeg?auto=compress&cs=tinysrgb&w=1600",
        "title_en": "The First Glance",
        "title_hi": "प्रथम दर्शन",
        "beat_en": "Their eyes meet — the world stills.",
        "beat_hi": "दो नयनों की एक भेंट — संसार ठहर गया।",
        "narration": "राम की दृष्टि उद्यान के जालीदार झरोखे से उठी, और उसी क्षण सीता ने भी पलटकर देखा — एक क्षण, और संसार थम गया।",
    },
]

W, H = 1280, 720
FPS = 30


def run(cmd, check=True):
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and proc.returncode != 0:
        print("FFMPEG ERROR:\n", proc.stderr[-1500:])
        raise SystemExit(1)
    return proc


def esc(t):
    return (
        t.replace("\\", "\\\\")
         .replace(":", r"\:")
         .replace("'", "\u2019")
         .replace(",", r"\,")
    )


def download_images():
    print(">>> Downloading Unsplash imagery (free-license)…")
    for s in SCENES:
        path = STORAGE / f"demo_ramayan_{s['id']}_bg.jpg"
        if path.exists() and path.stat().st_size > 30_000:
            print(f"  [skip] {path.name} already exists ({path.stat().st_size/1024:.0f} KB)")
            continue
        print(f"  [dl]   {s['id']}: {s['img_url'][:60]}…")
        with httpx.stream("GET", s["img_url"], timeout=30, follow_redirects=True) as r:
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_bytes(64 * 1024):
                    f.write(chunk)
        print(f"         -> {path.stat().st_size/1024:.0f} KB")


def make_scene(scene, dur=6.5):
    """Ken-Burns pan/zoom of the stock image with cinematic text overlay burned into the video.
    Produces one MP4 scene ready for concat_with_subs."""
    bg = f"demo_ramayan_{scene['id']}_bg.jpg"
    out = f"demo_ramayan_{scene['id']}_scene.mp4"
    print(f"  [scene] {scene['id']}  ({scene['title_en']})")

    frames = int(FPS * dur)
    # Ken-Burns zoom only — zoompan's x/y can't reference `t` or `w`; using constants.
    if scene["id"] == "sc1":
        zoom_expr = "min(zoom+0.0015,1.20)"
        xy_expr = "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
    elif scene["id"] == "sc2":
        zoom_expr = "min(zoom+0.0020,1.24)"
        # Slow slight drift using `on` (output frame number)
        xy_expr = "x='iw/2-(iw/zoom/2)+(on/60)':y='ih/2-(ih/zoom/2)'"
    else:
        zoom_expr = "min(zoom+0.0022,1.26)"
        xy_expr = "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)-(on/80)'"

    kb_filter = (
        f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,"
        f"crop={W*2}:{H*2},"
        f"zoompan=z='{zoom_expr}':d={frames}:{xy_expr}:s={W}x{H}:fps={FPS}"
    )
    # Add cinematic color grading (warm saffron/gold, slight vignette)
    color_grade = (
        "curves=r='0/0 0.5/0.55 1/1':g='0/0 0.5/0.48 1/0.95':b='0/0 0.5/0.42 1/0.8',"
        "eq=saturation=1.15:contrast=1.1"
    )
    # Vignette + bottom gradient for text readability
    vignette = (
        "vignette=PI/4.5,"
        f"drawbox=x=0:y={H-160}:w={W}:h=160:color=black@0.55:t=fill"
    )
    # Text overlays
    text_layers = []
    # English title (top)
    text_layers.append(
        f"drawtext=fontfile={FONT_SANS}:text='{esc(scene['title_en'].upper())}':"
        f"fontcolor=0xD4AF37:fontsize=22:x=64:y=64:"
        f"alpha='if(lt(t,0.6),(t/0.6),if(gt(t,{dur-0.6}),(({dur}-t)/0.6),1))'"
    )
    # Hindi title (top)
    text_layers.append(
        f"drawtext=fontfile={FONT_HINDI}:text='{esc(scene['title_hi'])}':"
        f"fontcolor=0xF3E4C3:fontsize=42:x=64:y=98:"
        f"alpha='if(lt(t,0.8),(t/0.8),if(gt(t,{dur-0.6}),(({dur}-t)/0.6),1))'"
    )
    # Bottom Hindi beat
    text_layers.append(
        f"drawtext=fontfile={FONT_HINDI}:text='{esc(scene['beat_hi'])}':"
        f"fontcolor=white:fontsize=32:x=(w-text_w)/2:y=h-100:"
        f"alpha='if(lt(t,1.2),max(0,(t-0.6)/0.6),if(gt(t,{dur-0.6}),(({dur}-t)/0.6),1))'"
    )
    # Small English beat below
    text_layers.append(
        f"drawtext=fontfile={FONT_ITALIC}:text='{esc(scene['beat_en'])}':"
        f"fontcolor=0xD4AF37:fontsize=20:x=(w-text_w)/2:y=h-56:"
        f"alpha='if(lt(t,1.6),max(0,(t-1.0)/0.6),if(gt(t,{dur-0.6}),(({dur}-t)/0.6),1))'"
    )
    # Corner branding
    text_layers.append(
        f"drawtext=fontfile={FONT_SANS}:text='AIPILLU  \u2022  RAMAYAN':"
        f"fontcolor=0xD4AF37@0.8:fontsize=12:x=w-text_w-64:y=64"
    )
    # Gold border strip bottom
    text_layers.append(f"drawbox=x=0:y=h-4:w={W}:h=4:color=0xD4AF37@0.75:t=fill")

    filter_chain = f"{kb_filter},{color_grade},{vignette},{','.join(text_layers)},format=yuv420p"

    cmd = (
        f'ffmpeg -y -loop 1 -i "{STORAGE/bg}" '
        f'-f lavfi -i "anullsrc=channel_layout=stereo:sample_rate=44100" '
        f'-vf "{filter_chain}" '
        f'-t {dur} '
        f'-c:v libx264 -profile:v baseline -level 3.0 -pix_fmt yuv420p -preset veryfast -crf 22 '
        f'-c:a aac -b:a 96k -shortest -movflags +faststart '
        f'"{STORAGE/out}"'
    )
    run(cmd)
    print(f"          -> {out}")
    return out


def to_webm(mp4_path: Path):
    webm = mp4_path.with_suffix(".webm")
    cmd = (
        f'ffmpeg -y -i "{mp4_path}" '
        f'-c:v libvpx-vp9 -b:v 0 -crf 34 -deadline realtime -cpu-used 8 '
        f'-c:a libopus -b:a 64k "{webm}"'
    )
    run(cmd)
    print(f"  [webm] {webm.name}  ({webm.stat().st_size/1024:.0f} KB)")


def poster(mp4_path: Path):
    out = mp4_path.with_name(mp4_path.stem + "_poster.jpg")
    cmd = f'ffmpeg -y -ss 2.5 -i "{mp4_path}" -frames:v 1 -q:v 3 "{out}"'
    run(cmd)
    print(f"  [poster] {out.name}")


def main():
    STORAGE.mkdir(parents=True, exist_ok=True)
    download_images()
    print(">>> Rendering per-scene Ken-Burns clips…")
    scene_files = []
    narrations = []
    for s in SCENES:
        scene_files.append(make_scene(s, dur=6.5))
        narrations.append(s["narration"])
    print(">>> Concatenating with soft subtitles…")
    final = "demo_ramayan.mp4"
    srt = "demo_ramayan.srt"
    assembly.concat_with_subs(scene_files, narrations, final, srt)
    mp4_path = STORAGE / final
    print(f"  [final] {mp4_path.name}  ({mp4_path.stat().st_size/1024:.0f} KB)")
    to_webm(mp4_path)
    poster(mp4_path)
    # Cleanup intermediate scene files
    for f in scene_files:
        (STORAGE / f).unlink(missing_ok=True)
    print("\n✅ Cinematic Ramayan demo generated.")


if __name__ == "__main__":
    main()
