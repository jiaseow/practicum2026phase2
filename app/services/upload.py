from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.schemas.upload import UploadVideoResponse


UPLOAD_DIR = Path("uploads")
ALLOWED_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm"}
MAX_UPLOAD_BYTES = 750 * 1024 * 1024


async def store_uploaded_video(*, project_id: str, file: UploadFile) -> UploadVideoResponse:
    if not project_id.strip():
        raise ValueError("projectId is required.")
    if not file.filename:
        raise ValueError("Uploaded file must include a filename.")

    original_filename = file.filename
    suffix = Path(original_filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        allowed = ", ".join(sorted(ALLOWED_SUFFIXES))
        raise ValueError(f"Unsupported video type. Allowed extensions: {allowed}.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_project_id = sanitize_name(project_id)
    safe_stem = sanitize_name(Path(original_filename).stem)
    stored_filename = f"{safe_project_id}-{uuid4().hex[:12]}-{safe_stem}{suffix}"
    destination = (UPLOAD_DIR / stored_filename).resolve()

    size_bytes = 0
    with destination.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            size_bytes += len(chunk)
            if size_bytes > MAX_UPLOAD_BYTES:
                destination.unlink(missing_ok=True)
                raise ValueError("Uploaded video exceeds the 750 MB limit.")
            output.write(chunk)

    return UploadVideoResponse(
        projectId=project_id,
        filename=stored_filename,
        originalFilename=original_filename,
        videoPath=destination.as_uri(),
        contentType=file.content_type or "application/octet-stream",
        sizeBytes=size_bytes,
    )


def sanitize_name(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip(".-")
    return sanitized[:80] or "upload"
