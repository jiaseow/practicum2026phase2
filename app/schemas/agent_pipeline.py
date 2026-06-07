from pydantic import BaseModel, ConfigDict, Field

from app.schemas.analyze_repo import AnalyzeRepoResponse
from app.schemas.extract_claims import ExtractClaimsResponse
from app.schemas.verify import TranscriptSearchChunk, VerifyResponse


class AgentRunMetadata(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    agent_name: str = Field(alias="agentName")
    sdk: str


class RepoComparisonRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: str = Field(..., alias="projectId")
    repo_url: str = Field(..., alias="repoUrl")
    description: str
    transcript_chunks: list[TranscriptSearchChunk] = Field(default_factory=list, alias="transcriptChunks")


class RepoComparisonResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: str = Field(alias="projectId")
    repository_analysis: AnalyzeRepoResponse = Field(alias="repositoryAnalysis")
    claim_extraction: ExtractClaimsResponse = Field(alias="claimExtraction")
    verification: VerifyResponse
    agent: AgentRunMetadata
