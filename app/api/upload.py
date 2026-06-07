from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.schemas.upload import UploadVideoResponse
from app.schemas.transcribe import TranscribeResponse
from app.services.transcript_upload import process_uploaded_transcript
from app.services.upload import store_uploaded_video

router = APIRouter()


@router.post("/upload-video", response_model=UploadVideoResponse)
async def upload_video(
    project_id: str = Form(..., alias="projectId"),
    file: UploadFile = File(...),
) -> UploadVideoResponse:
    try:
        return await store_uploaded_video(project_id=project_id, file=file)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post("/process-transcript-file", response_model=TranscribeResponse)
async def process_transcript_file(
    project_id: str = Form(..., alias="projectId"),
    file: UploadFile = File(...),
) -> TranscribeResponse:
    try:
        return await process_uploaded_transcript(project_id=project_id, file=file)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
