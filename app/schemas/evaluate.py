from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class EvaluateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: str = Field(..., alias="projectId")
    video_path: str = Field(..., alias="videoPath")
    repo_url: str = Field(..., alias="repoUrl")
    description: str
    company_relevance: dict = Field(default_factory=dict, alias="companyRelevance")
    evaluation_notes: list[str] = Field(default_factory=list, alias="evaluationNotes")
    skip_transcription: bool = Field(default=False, alias="skipTranscription")
    transcript_override: Optional[str] = Field(default=None, alias="transcriptOverride")
