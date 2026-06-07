from fastapi import APIRouter, HTTPException, status

from app.schemas.analyze_repo import AnalyzeRepoRequest, AnalyzeRepoResponse
from app.services.repo_analysis import analyze_repository

router = APIRouter()


@router.post("/analyze-repo", response_model=AnalyzeRepoResponse)
def analyze_repo(request: AnalyzeRepoRequest) -> AnalyzeRepoResponse:
    try:
        return analyze_repository(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
