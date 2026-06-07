from __future__ import annotations

from itertools import zip_longest

from app.core.config import get_settings
from app.db.transcripts import store_transcript
from app.schemas.transcribe import TranscriptChunk, TranscribeRequest, TranscribeResponse
from app.services.chunking import chunk_transcript, chunk_transcript_segments
from app.services.media import prepare_audio, resolve_local_media_path
from app.services.openai_client import embed_texts, transcribe_audio


async def transcribe_project_video(request: TranscribeRequest) -> TranscribeResponse:
    settings = get_settings()
    media_path = resolve_local_media_path(request.video_path)

    audio_path = prepare_audio(media_path, media_path.parent)
    transcript, duration, segments = await transcribe_audio(audio_path)

    if not transcript:
        raise ValueError("Whisper returned an empty transcript.")

    chunks = (
        chunk_transcript_segments(
            segments,
            project_id=request.project_id,
            target_tokens=settings.chunk_target_tokens,
            overlap_tokens=settings.chunk_overlap_tokens,
        )
        if segments
        else chunk_transcript(
            transcript,
            project_id=request.project_id,
            duration=duration,
            target_tokens=settings.chunk_target_tokens,
            overlap_tokens=settings.chunk_overlap_tokens,
        )
    )
    embeddings = await embed_texts([chunk.text for chunk in chunks])

    stored = store_transcript(
        project_id=request.project_id,
        transcript=transcript,
        duration=duration,
        chunks=chunks,
        embeddings=embeddings,
    )
    if not stored:
        raise ValueError("Transcript was embedded, but pgvector storage is unavailable. Check DATABASE_URL and the Docker PostgreSQL container.")

    return TranscribeResponse(
        projectId=request.project_id,
        transcript=transcript,
        duration=duration,
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
