from __future__ import annotations

from itertools import zip_longest

from app.core.config import get_settings
from app.db.transcripts import store_transcript
from app.schemas.agent_pipeline import RepoComparisonRequest
from app.schemas.evaluate import EvaluateRequest
from app.schemas.report import ReportInputBundle, ReportResponse
from app.schemas.transcribe import TranscriptChunk, TranscribeRequest, TranscribeResponse
from app.schemas.verify import TranscriptSearchChunk
from app.services.agent_pipeline import assemble_report_with_agent, compare_repo_claims_with_agent
from app.services.chunking import chunk_transcript
from app.services.openai_client import embed_texts
from app.services.transcription import transcribe_project_video


async def evaluate_project(request: EvaluateRequest) -> ReportResponse:
    transcription = await build_transcription(request)
    comparison = await compare_repo_claims_with_agent(
        RepoComparisonRequest(
            projectId=request.project_id,
            repoUrl=request.repo_url,
            description=request.description,
            transcriptChunks=[
                TranscriptSearchChunk(
                    id=chunk.id,
                    text=chunk.text,
                    startTime=chunk.start_time,
                    endTime=chunk.end_time,
                )
                for chunk in transcription.chunks
            ],
        )
    )

    return await assemble_report_with_agent(
        ReportInputBundle(
            projectId=request.project_id,
            repoUrl=request.repo_url,
            description=request.description,
            transcription=transcription,
            repositoryAnalysis=comparison.repository_analysis,
            claimExtraction=comparison.claim_extraction,
            verification=comparison.verification,
            companyRelevance=request.company_relevance,
            evaluationNotes=request.evaluation_notes,
        )
    )


async def build_transcription(request: EvaluateRequest) -> TranscribeResponse:
    if not request.skip_transcription:
        return await transcribe_project_video(
            TranscribeRequest(projectId=request.project_id, videoPath=request.video_path)
        )

    transcript = (request.transcript_override or "").strip()
    if not transcript:
        raise ValueError("transcriptOverride is required when skipTranscription is true.")

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
        source="manual-transcript",
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
            for chunk, embedding in require_matching_chunks_and_embeddings(chunks, embeddings)
        ]
        or [
            TranscriptChunk(
                id=f"{request.project_id}-manual-transcript-1",
                text=transcript,
                startTime=0,
                endTime=0,
                embedding=[],
            )
        ],
    )


def require_matching_chunks_and_embeddings(chunks, embeddings):
    for chunk, embedding in zip_longest(chunks, embeddings):
        if chunk is None or embedding is None:
            raise ValueError("Chunk and embedding counts do not match.")
        yield chunk, embedding
