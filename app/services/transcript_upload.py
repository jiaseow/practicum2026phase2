from __future__ import annotations

from itertools import zip_longest
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import get_settings
from app.db.transcripts import store_transcript
from app.schemas.transcribe import TranscriptChunk, TranscriptTextRequest, TranscribeResponse
from app.services.chunking import chunk_transcript
from app.services.openai_client import embed_texts
from app.services.upload import UPLOAD_DIR, sanitize_name


ALLOWED_TRANSCRIPT_SUFFIXES = {".txt"}
MAX_TRANSCRIPT_BYTES = 5 * 1024 * 1024


async def process_uploaded_transcript(*, project_id: str, file: UploadFile) -> TranscribeResponse:
    if not project_id.strip():
        raise ValueError("projectId is required.")
    if not file.filename:
        raise ValueError("Uploaded transcript must include a filename.")

    original_filename = file.filename
    suffix = Path(original_filename).suffix.lower()
    if suffix not in ALLOWED_TRANSCRIPT_SUFFIXES:
        raise ValueError("Transcript file must be a .txt file.")

    transcript_bytes = await file.read()
    if len(transcript_bytes) > MAX_TRANSCRIPT_BYTES:
        raise ValueError("Transcript file exceeds the 5 MB limit.")

    try:
        transcript = transcript_bytes.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise ValueError("Transcript file must be UTF-8 text.") from exc

    if not transcript:
        raise ValueError("Transcript file is empty.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_project_id = sanitize_name(project_id)
    safe_stem = sanitize_name(Path(original_filename).stem)
    stored_filename = f"{safe_project_id}-{uuid4().hex[:12]}-{safe_stem}{suffix}"
    destination = (UPLOAD_DIR / stored_filename).resolve()
    destination.write_bytes(transcript_bytes)

    return await process_transcript_text(
        TranscriptTextRequest(
            projectId=project_id,
            transcript=transcript,
            sourceName=original_filename,
        )
    )


async def process_transcript_text(request: TranscriptTextRequest) -> TranscribeResponse:
    transcript = request.transcript.strip()
    if not transcript:
        raise ValueError("Transcript text is required.")

    settings = get_settings()
    chunks = chunk_transcript(
        transcript,
        project_id=request.project_id,
        duration=None,
        target_tokens=settings.chunk_target_tokens,
        overlap_tokens=settings.chunk_overlap_tokens,
    )
    embeddings = await embed_texts([chunk.text for chunk in chunks])
    stored = store_transcript(
        project_id=request.project_id,
        transcript=transcript,
        duration=None,
        chunks=chunks,
        embeddings=embeddings,
        source=request.source_name,
    )
    if not stored:
        raise ValueError("Transcript was embedded, but pgvector storage is unavailable. Check DATABASE_URL and the Docker PostgreSQL container.")

    return TranscribeResponse(
        projectId=request.project_id,
        transcript=transcript,
        duration=None,
        chunks=[
            TranscriptChunk(
                id=chunk.id,
                text=chunk.text,
                startTime=chunk.start_time,
                endTime=chunk.end_time,
                embedding=embedding,
            )
            for chunk, embedding in _zip_chunks_and_embeddings(chunks, embeddings)
        ],
    )


def _zip_chunks_and_embeddings(chunks, embeddings):
    for chunk, embedding in zip_longest(chunks, embeddings):
        if chunk is None or embedding is None:
            raise ValueError("Chunk and embedding counts do not match.")
        yield chunk, embedding
