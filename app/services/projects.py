from __future__ import annotations

from datetime import datetime

import psycopg

from app.db.transcripts import delete_transcript, get_transcript_summary
from app.schemas.projects import (
    ProjectDeleteResponse,
    ProjectStatusResponse,
    TranscriptStatus,
    UploadedVideoInfo,
)
from app.services.upload import UPLOAD_DIR, sanitize_name


def get_project_status(project_id: str) -> ProjectStatusResponse:
    uploads = list_uploaded_videos(project_id)
    transcript = get_project_transcript_status(project_id)
    return ProjectStatusResponse(
        projectId=project_id,
        uploads=uploads,
        transcript=transcript,
        readyForEvaluation=bool(uploads),
    )


def delete_project(project_id: str) -> ProjectDeleteResponse:
    deleted_uploads = delete_uploaded_videos(project_id)
    try:
        deleted_transcript = delete_transcript(project_id)
    except psycopg.OperationalError as exc:
        return ProjectDeleteResponse(
            projectId=project_id,
            deletedUploads=deleted_uploads,
            deletedTranscript=False,
            storageAvailable=False,
            error=str(exc),
        )

    return ProjectDeleteResponse(
        projectId=project_id,
        deletedUploads=deleted_uploads,
        deletedTranscript=deleted_transcript,
        storageAvailable=True,
    )


def list_uploaded_videos(project_id: str) -> list[UploadedVideoInfo]:
    if not UPLOAD_DIR.exists():
        return []

    prefix = sanitize_name(project_id) + "-"
    uploads: list[UploadedVideoInfo] = []
    for path in sorted(UPLOAD_DIR.glob(prefix + "*"), key=lambda item: item.stat().st_mtime, reverse=True):
        if not path.is_file() or path.name == ".gitkeep":
            continue
        stat = path.stat()
        uploads.append(
            UploadedVideoInfo(
                filename=path.name,
                videoPath=path.resolve().as_uri(),
                sizeBytes=stat.st_size,
                modifiedAt=datetime.fromtimestamp(stat.st_mtime).astimezone(),
            )
        )
    return uploads


def delete_uploaded_videos(project_id: str) -> int:
    count = 0
    for upload in list_uploaded_videos(project_id):
        path = UPLOAD_DIR / upload.filename
        if not path.exists() or not path.is_file():
            continue
        path.unlink()
        count += 1
    return count


def get_project_transcript_status(project_id: str) -> TranscriptStatus:
    try:
        summary = get_transcript_summary(project_id)
    except psycopg.OperationalError as exc:
        return TranscriptStatus(
            available=False,
            storageAvailable=False,
            chunkCount=0,
            error=str(exc),
        )

    if summary is None:
        return TranscriptStatus(
            available=False,
            storageAvailable=True,
            chunkCount=0,
        )

    return TranscriptStatus(
        available=True,
        storageAvailable=True,
        chunkCount=summary["chunk_count"],
        duration=summary["duration"],
        createdAt=summary["created_at"],
    )
