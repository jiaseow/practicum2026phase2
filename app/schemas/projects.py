from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UploadedVideoInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    filename: str
    video_path: str = Field(alias="videoPath")
    size_bytes: int = Field(alias="sizeBytes")
    modified_at: datetime = Field(alias="modifiedAt")


class TranscriptStatus(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    available: bool
    storage_available: bool = Field(alias="storageAvailable")
    chunk_count: int = Field(alias="chunkCount")
    duration: Optional[float] = None
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")
    error: Optional[str] = None


class ProjectStatusResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: str = Field(alias="projectId")
    uploads: list[UploadedVideoInfo]
    transcript: TranscriptStatus
    ready_for_evaluation: bool = Field(alias="readyForEvaluation")


class ProjectDeleteResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: str = Field(alias="projectId")
    deleted_uploads: int = Field(alias="deletedUploads")
    deleted_transcript: bool = Field(alias="deletedTranscript")
    storage_available: bool = Field(alias="storageAvailable")
    error: Optional[str] = None
