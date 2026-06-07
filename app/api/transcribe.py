from fastapi import APIRouter, HTTPException, status

from app.schemas.transcribe import TranscriptTextRequest, TranscribeRequest, TranscribeResponse
from app.services.transcript_upload import process_transcript_text
from app.services.transcription import transcribe_project_video

router = APIRouter()


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(request: TranscribeRequest) -> TranscribeResponse:
    try:
        return await transcribe_project_video(request)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post("/process-transcript-text", response_model=TranscribeResponse)
async def process_transcript_text_endpoint(request: TranscriptTextRequest) -> TranscribeResponse:
    try:
        return await process_transcript_text(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
