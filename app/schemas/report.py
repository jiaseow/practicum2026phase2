from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.analyze_repo import AnalyzeRepoResponse
from app.schemas.extract_claims import ExtractClaimsResponse
from app.schemas.transcribe import TranscribeResponse
from app.schemas.verify import VerifyResponse


class ProjectMetadata(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: str = Field(alias="projectId")
    repo_url: Optional[str] = Field(default=None, alias="repoUrl")
    generated_at: datetime = Field(alias="generatedAt")
    system_version: str = Field(alias="systemVersion")
    model_versions: dict[str, str] = Field(alias="modelVersions")


class ReportSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total_claims: int = Field(alias="totalClaims")
    verified_claims: int = Field(alias="verifiedClaims")
    partial_claims: int = Field(alias="partialClaims")
    unverified_claims: int = Field(alias="unverifiedClaims")
    contradicted_claims: int = Field(alias="contradictedClaims")
    detected_technologies: int = Field(alias="detectedTechnologies")
    transcript_chunks: int = Field(alias="transcriptChunks")
    risk_level: str = Field(alias="riskLevel")


class RiskItem(BaseModel):
    severity: str
    code: str
    message: str


class ReportInputBundle(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: str = Field(..., alias="projectId")
    repo_url: Optional[str] = Field(default=None, alias="repoUrl")
    description: Optional[str] = None
    transcription: Optional[TranscribeResponse] = None
    repository_analysis: Optional[AnalyzeRepoResponse] = Field(default=None, alias="repositoryAnalysis")
    claim_extraction: Optional[ExtractClaimsResponse] = Field(default=None, alias="claimExtraction")
    verification: VerifyResponse
    company_relevance: dict[str, Any] = Field(default_factory=dict, alias="companyRelevance")
    evaluation_notes: list[str] = Field(default_factory=list, alias="evaluationNotes")


class ReportResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_metadata: ProjectMetadata = Field(alias="project_metadata")
    summary: ReportSummary
    claims: dict[str, Any]
    detection: dict[str, Any]
    verification: dict[str, Any]
    transcript: dict[str, Any]
    repository: dict[str, Any]
    company_relevance: dict[str, Any] = Field(alias="company_relevance")
    risks_and_gaps: dict[str, Any] = Field(alias="risks_and_gaps")
    evaluation_notes: dict[str, Any] = Field(alias="evaluation_notes")


class SavedReportItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: str = Field(alias="projectId")
    repo_url: Optional[str] = Field(default=None, alias="repoUrl")
    generated_at: datetime = Field(alias="generatedAt")
    risk_level: str = Field(alias="riskLevel")
    total_claims: int = Field(alias="totalClaims")
    verified_claims: int = Field(alias="verifiedClaims")
    unverified_claims: int = Field(alias="unverifiedClaims")
    contradicted_claims: int = Field(alias="contradictedClaims")
    path: str


class SavedReportsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    reports: list[SavedReportItem]
    count: int
