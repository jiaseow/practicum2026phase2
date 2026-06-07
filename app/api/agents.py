from fastapi import APIRouter, HTTPException, status

from app.schemas.agent_pipeline import RepoComparisonRequest, RepoComparisonResponse
from app.schemas.report import ReportInputBundle, ReportResponse
from app.services.agent_pipeline import (
    assemble_report_with_agent,
    compare_repo_claims_with_agent,
)

router = APIRouter()


@router.post("/agents/compare", response_model=RepoComparisonResponse)
async def compare_with_agent(request: RepoComparisonRequest) -> RepoComparisonResponse:
    try:
        return await compare_repo_claims_with_agent(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post("/agents/report", response_model=ReportResponse)
async def report_with_agent(request: ReportInputBundle) -> ReportResponse:
    try:
        return await assemble_report_with_agent(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
