from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AnalyzeRepoRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    repo_url: str = Field(..., alias="repoUrl")
    project_id: str = Field(..., alias="projectId")


class TechnologyEvidence(BaseModel):
    file: str
    line: int
    snippet: str
    source: str


class DetectedTechnology(BaseModel):
    key: str
    name: str
    category: str
    confidence: str
    evidence: list[TechnologyEvidence]


class RepositoryScanSummary(BaseModel):
    scanned_files: int = Field(alias="scannedFiles")
    evidence_count: int = Field(alias="evidenceCount")
    truncated: bool
    clone_seconds: Optional[float] = Field(default=None, alias="cloneSeconds")


class AnalyzeRepoResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: str = Field(alias="projectId")
    repo_url: str = Field(alias="repoUrl")
    detected_techs: list[DetectedTechnology] = Field(alias="detectedTechs")
    repository: RepositoryScanSummary
