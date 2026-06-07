from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse


SUPPORTED_VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm"}
SUPPORTED_AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}


def resolve_local_media_path(video_path: str) -> Path:
    parsed = urlparse(video_path)
    if parsed.scheme == "file":
        path = Path(parsed.path)
    elif parsed.scheme in {"", None}:
        path = Path(video_path)
    else:
        raise ValueError("Only local file paths and file:// URLs are supported in the first endpoint.")

    if not path.exists():
        raise FileNotFoundError(f"Media file not found: {path}")
    if path.suffix.lower() not in SUPPORTED_VIDEO_SUFFIXES | SUPPORTED_AUDIO_SUFFIXES:
        raise ValueError(f"Unsupported media file type: {path.suffix}")
    return path


def prepare_audio(media_path: Path, output_dir: Path) -> Path:
    if media_path.suffix.lower() in SUPPORTED_AUDIO_SUFFIXES | {".mp4", ".webm"}:
        return media_path

    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        return media_path

    output_dir.mkdir(parents=True, exist_ok=True)
    audio_path = output_dir / f"{media_path.stem}.mp3"
    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(media_path),
        "-vn",
        "-acodec",
        "libmp3lame",
        "-ar",
        "44100",
        "-ac",
        "2",
        str(audio_path),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"ffmpeg failed to extract audio: {stderr}") from exc
    return audio_path
