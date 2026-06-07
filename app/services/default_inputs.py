from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from app.core.config import get_settings
from app.schemas.default_inputs import DefaultInputsResponse


def load_default_inputs() -> DefaultInputsResponse:
    settings = get_settings()
    errors: list[str] = []

    video_path, video_filename = load_default_video(settings.default_video_path, errors)
    transcript, transcript_filename = load_text_file(
        settings.default_transcript_path,
        "transcript",
        errors,
        allowed_suffixes={".txt"},
    )
    readme, readme_filename = load_text_file(
        settings.default_readme_path,
        "README",
        errors,
        allowed_suffixes={".md", ".markdown", ".txt"},
    )

    return DefaultInputsResponse(
        projectId=settings.default_project_id or None,
        repoUrl=settings.default_repo_url or None,
        videoPath=video_path,
        videoFilename=video_filename,
        transcript=transcript,
        transcriptFilename=transcript_filename,
        readme=readme,
        readmeFilename=readme_filename,
        errors=errors,
    )


def load_default_video(configured_path: str, errors: list[str]) -> tuple[str | None, str | None]:
    if not configured_path:
        return None, None

    path = resolve_configured_path(configured_path)
    if not path.exists() or not path.is_file():
        errors.append(f"Default video file was not found: {path}")
        return None, None

    if path.suffix.lower() != ".mp4":
        errors.append("Default video must be an .mp4 file.")
        return None, None

    return path.resolve().as_uri(), path.name


def load_text_file(
    configured_path: str,
    label: str,
    errors: list[str],
    *,
    allowed_suffixes: set[str],
) -> tuple[str | None, str | None]:
    if not configured_path:
        return None, None

    path = resolve_configured_path(configured_path)
    if not path.exists() or not path.is_file():
        errors.append(f"Default {label} file was not found: {path}")
        return None, None

    if path.suffix.lower() not in allowed_suffixes:
        allowed = ", ".join(sorted(allowed_suffixes))
        errors.append(f"Default {label} file must use one of: {allowed}.")
        return None, None

    try:
        text = path.read_text(encoding="utf-8").strip()
    except UnicodeDecodeError:
        errors.append(f"Default {label} file must be UTF-8 text.")
        return None, None

    if not text:
        errors.append(f"Default {label} file is empty.")
        return None, None

    return text, path.name


def resolve_configured_path(value: str) -> Path:
    if value.startswith("file://"):
        parsed = urlparse(value)
        return Path(parsed.path).expanduser()
    return Path(value).expanduser()
