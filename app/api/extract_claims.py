from fastapi import APIRouter, HTTPException, status

from app.schemas.extract_claims import ExtractClaimsRequest, ExtractClaimsResponse
from app.services.claim_extraction import extract_claims

router = APIRouter()


@router.post("/extract-claims", response_model=ExtractClaimsResponse)
def extract_claims_endpoint(request: ExtractClaimsRequest) -> ExtractClaimsResponse:
    try:
        return extract_claims(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
