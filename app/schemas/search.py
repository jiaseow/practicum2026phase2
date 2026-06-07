from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SearchRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: str = Field(..., alias="projectId")
    query: str
    limit: int = Field(default=5, ge=1, le=20)
    similarity_threshold: float = Field(default=0.7, ge=0, le=1, alias="similarityThreshold")


class TranscriptSearchResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    text: str
    start_time: float = Field(alias="startTime")
    end_time: float = Field(alias="endTime")
    similarity: float
    metadata: dict


class SearchResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: str = Field(alias="projectId")
    query: str
    results: list[TranscriptSearchResult]
    result_count: int = Field(alias="resultCount")
    embedding_model: Optional[str] = Field(default=None, alias="embeddingModel")
