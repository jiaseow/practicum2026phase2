from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TranscribeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    video_path: str = Field(..., alias="videoPath")
    project_id: str = Field(..., alias="projectId")


class TranscriptTextRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: str = Field(..., alias="projectId")
    transcript: str
    source_name: str = Field(default="default-transcript.txt", alias="sourceName")


class TranscriptChunk(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    text: str
    start_time: float = Field(alias="startTime")
    end_time: float = Field(alias="endTime")
    embedding: list[float]


class TranscribeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: str = Field(alias="projectId")
    transcript: str
    chunks: list[TranscriptChunk]
    duration: Optional[float] = None
