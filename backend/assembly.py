"""Video assembly using ffmpeg: adds narration + subtitles to a scene clip,
then concatenates all scenes into a final film."""
from __future__ import annotations
import os
import json
import subprocess
import shlex
from pathlib import Path

STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "/app/backend/storage"))


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {' '.join(shlex.quote(c) for c in cmd)}\nSTDERR:\n{proc.stderr[-1500:]}")


def probe_duration(filename: str) -> float:
    """Return duration in seconds using ffprobe."""
    path = STORAGE_DIR / filename
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "json", str(path)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return 0.0
    try:
        return float(json.loads(proc.stdout).get("format", {}).get("duration", 0.0))
    except Exception:
        return 0.0


def _fmt_srt_ts(t: float) -> str:
    if t < 0:
        t = 0
    hours = int(t // 3600)
    minutes = int((t % 3600) // 60)
    seconds = int(t % 60)
    millis = int((t - int(t)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def build_srt(entries: list[dict]) -> str:
    """entries: [{start, end, text}, ...] — returns full SRT string."""
    lines = []
    for i, e in enumerate(entries, start=1):
        text = (e.get("text") or "").strip()
        if not text:
            continue
        lines.append(str(i))
        lines.append(f"{_fmt_srt_ts(e['start'])} --> {_fmt_srt_ts(e['end'])}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def write_srt(out_name: str, srt_content: str) -> str:
    path = STORAGE_DIR / out_name
    path.write_text(srt_content, encoding="utf-8")
    return out_name


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


def attach_soft_subs(video_file: str, srt_file: str, out_name: str) -> str:
    """Copy video/audio streams and add SRT as a soft subtitle track (mov_text — MP4-compatible)."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(STORAGE_DIR / video_file),
        "-i", str(STORAGE_DIR / srt_file),
        "-c:v", "copy", "-c:a", "copy",
        "-c:s", "mov_text",
        "-metadata:s:s:0", "language=und",
        "-metadata:s:s:0", "title=Narration",
        str(STORAGE_DIR / out_name),
    ]
    _run(cmd)
    return out_name


def concat_with_subs(scene_files: list[str], scene_narrations: list[str], out_name: str, srt_name: str) -> tuple[str, str]:
    """Concatenate scene videos AND produce a proper SRT + a subtitled MP4.
    scene_files[i] pairs with scene_narrations[i]. Returns (video_out, srt_out).
    """
    if not scene_files:
        raise ValueError("No scenes to concatenate")
    if len(scene_files) != len(scene_narrations):
        # Pad narrations to match
        scene_narrations = list(scene_narrations) + [""] * (len(scene_files) - len(scene_narrations))

    # 1) Probe durations and build SRT with proper cumulative timings
    entries = []
    cursor = 0.0
    for f, text in zip(scene_files, scene_narrations):
        dur = probe_duration(f)
        # Show subtitle for the middle 80% of the clip, min 1s, max 8s per line
        pad = max(0.15, min(0.5, dur * 0.1))
        entries.append({
            "start": cursor + pad,
            "end": cursor + max(1.0, dur - pad),
            "text": (text or "").strip(),
        })
        cursor += dur

    srt = build_srt(entries)
    write_srt(srt_name, srt)

    # 2) Concat plain mp4
    raw_concat = f"_raw_{out_name}"
    concat_scenes(scene_files, raw_concat)

    # 3) Attach soft subs (mov_text) to the concatenated file
    try:
        attach_soft_subs(raw_concat, srt_name, out_name)
    finally:
        # Clean up the intermediate raw concat
        try:
            (STORAGE_DIR / raw_concat).unlink()
        except Exception:
            pass
    return out_name, srt_name


def concat_audio_files(audio_files: list[str], out_name: str) -> str:
    """Concatenate multiple mp3 audio files into a single mp3 (streams copied, no re-encode)."""
    if not audio_files:
        raise ValueError("No audio files to concatenate")
    if len(audio_files) == 1:
        src = STORAGE_DIR / audio_files[0]
        dst = STORAGE_DIR / out_name
        if src.resolve() != dst.resolve():
            dst.write_bytes(src.read_bytes())
        return out_name
    list_file = STORAGE_DIR / f"_aconcat_{out_name}.txt"
    lines = [f"file '{(STORAGE_DIR / af).as_posix()}'" for af in audio_files]
    list_file.write_text("\n".join(lines))
    out_path = STORAGE_DIR / out_name
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c:a", "libmp3lame", "-b:a", "128k",
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
