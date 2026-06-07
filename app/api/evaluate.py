from fastapi import APIRouter, HTTPException, status

from app.schemas.evaluate import EvaluateRequest
from app.schemas.report import ReportResponse
from app.services.evaluation import evaluate_project

router = APIRouter()


@router.post("/evaluate", response_model=ReportResponse)
async def evaluate(request: EvaluateRequest) -> ReportResponse:
    try:
        return await evaluate_project(request)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
