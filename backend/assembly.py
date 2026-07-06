"""Video assembly using ffmpeg: adds narration + subtitles to a scene clip,
then concatenates all scenes into a final film."""
from __future__ import annotations
import os
import subprocess
import shlex
from pathlib import Path

STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "/app/backend/storage"))


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {' '.join(shlex.quote(c) for c in cmd)}\nSTDERR:\n{proc.stderr[-1500:]}")


def mux_scene(video_file: str, audio_file: str | None, out_name: str, subtitle_text: str | None = None) -> str:
    """Combine a scene video with its narration audio; optionally burn subtitles.
    All paths are storage-relative filenames.
    """
    video_path = STORAGE_DIR / video_file
    out_path = STORAGE_DIR / out_name
    cmd = ["ffmpeg", "-y", "-i", str(video_path)]
    if audio_file:
        cmd += ["-i", str(STORAGE_DIR / audio_file)]

    filters = []
    if subtitle_text:
        # Escape for drawtext
        safe = subtitle_text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\u2019").replace("\n", " ")
        # Truncate long lines to keep readable
        if len(safe) > 220:
            safe = safe[:217] + "..."
        filters.append(
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            f":text='{safe}':fontcolor=white:fontsize=28:box=1:boxcolor=black@0.55:boxborderw=14"
            ":x=(w-text_w)/2:y=h-100"
        )

    if filters:
        cmd += ["-vf", ",".join(filters)]

    if audio_file:
        cmd += ["-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-c:a", "aac", "-shortest"]
    else:
        cmd += ["-c:v", "libx264", "-an"]

    cmd += ["-pix_fmt", "yuv420p", "-preset", "veryfast", str(out_path)]
    _run(cmd)
    return out_name


def concat_scenes(scene_files: list[str], out_name: str) -> str:
    """Concatenate multiple mp4 scene files (all same resolution) into a final film via concat demuxer."""
    if not scene_files:
        raise ValueError("No scenes to concatenate")
    list_file = STORAGE_DIR / f"_concat_{out_name}.txt"
    lines = [f"file '{(STORAGE_DIR / sf).as_posix()}'" for sf in scene_files]
    list_file.write_text("\n".join(lines))
    out_path = STORAGE_DIR / out_name
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p",
        "-preset", "veryfast",
        str(out_path),
    ]
    try:
        _run(cmd)
    finally:
        try:
            list_file.unlink()
        except Exception:
            pass
    return out_name


def image_to_video(image_file: str, out_name: str, duration: int = 4, size: str = "1280x720") -> str:
    """Fallback: create a Ken-Burns style video from a still image."""
    image_path = STORAGE_DIR / image_file
    out_path = STORAGE_DIR / out_name
    w, h = size.split("x")
    zoom_frames = int(25 * duration)
    vf = (
        f"scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h},"
        f"zoompan=z='min(zoom+0.0015,1.2)':d={zoom_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}"
    )
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", str(image_path),
        "-t", str(duration),
        "-vf", vf,
        "-r", "25",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast",
        str(out_path),
    ]
    _run(cmd)
    return out_name
