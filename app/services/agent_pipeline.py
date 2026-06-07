from __future__ import annotations

import asyncio

from app.schemas.agent_pipeline import (
    AgentRunMetadata,
    RepoComparisonRequest,
    RepoComparisonResponse,
)
from app.schemas.analyze_repo import AnalyzeRepoRequest
from app.schemas.extract_claims import ExtractClaimsRequest
from app.schemas.report import ReportInputBundle, ReportResponse
from app.schemas.verify import VerifyRequest
from app.services.claim_extraction import extract_claims
from app.services.repo_analysis import analyze_repository
from app.services.report_store import save_report
from app.services.reporting import assemble_report
from app.services.verification import verify_claims


REPO_AGENT_NAME = "Repository Evidence Agent"
REPORT_AGENT_NAME = "JSON Report Agent"
PIPELINE_RUNTIME = "deterministic-services"


async def compare_repo_claims_with_agent(request: RepoComparisonRequest) -> RepoComparisonResponse:
    repository_analysis = await asyncio.to_thread(
        analyze_repository,
        AnalyzeRepoRequest(
            projectId=request.project_id,
            repoUrl=request.repo_url,
        ),
    )
    claim_extraction = extract_claims(
        ExtractClaimsRequest(
            projectId=request.project_id,
            description=request.description,
        )
    )
    verification = verify_claims(
        VerifyRequest(
            projectId=request.project_id,
            claimedTechs=[
                claim.model_dump(by_alias=True)
                for claim in claim_extraction.claimed_techs
            ],
            detectedTechs=[
                tech.model_dump(by_alias=True)
                for tech in repository_analysis.detected_techs
            ],
            transcriptChunks=[
                chunk.model_dump(by_alias=True)
                for chunk in request.transcript_chunks
            ],
        )
    )

    return RepoComparisonResponse(
        projectId=request.project_id,
        repositoryAnalysis=repository_analysis,
        claimExtraction=claim_extraction,
        verification=verification,
        agent=AgentRunMetadata(agentName=REPO_AGENT_NAME, sdk=PIPELINE_RUNTIME),
    )


async def assemble_report_with_agent(bundle: ReportInputBundle) -> ReportResponse:
    report = assemble_report(bundle)
    save_report(report)
    return report
