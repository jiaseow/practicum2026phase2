from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class TranscriptSearchChunk(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = None
    text: str
    start_time: Optional[float] = Field(default=None, alias="startTime")
    end_time: Optional[float] = Field(default=None, alias="endTime")


class VerifyRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: str = Field(..., alias="projectId")
    claimed_techs: list[Any] = Field(default_factory=list, alias="claimedTechs")
    detected_techs: list[Any] = Field(default_factory=list, alias="detectedTechs")
    transcript_chunks: list[TranscriptSearchChunk] = Field(default_factory=list, alias="transcriptChunks")


class VerificationEvidence(BaseModel):
    source: str
    detail: str
    file: Optional[str] = None
    line: Optional[int] = None
    snippet: Optional[str] = None
    chunk_id: Optional[str] = Field(default=None, alias="chunkId")
    start_time: Optional[float] = Field(default=None, alias="startTime")
    end_time: Optional[float] = Field(default=None, alias="endTime")


class ClaimVerificationResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    key: str
    claimed: str
    detected: bool
    transcript_mentioned: bool = Field(alias="transcriptMentioned")
    status: str
    confidence: float
    evidence: list[VerificationEvidence]
    notes: list[str] = Field(default_factory=list)


class VerificationSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total_claims: int = Field(alias="totalClaims")
    verified: int
    partial: int
    unverified: int
    contradicted: int


class VerifyResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: str = Field(alias="projectId")
    claim_verification: list[ClaimVerificationResult] = Field(alias="claimVerification")
    summary: VerificationSummary
