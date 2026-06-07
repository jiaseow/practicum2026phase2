from fastapi import APIRouter

from app.schemas.verify import VerifyRequest, VerifyResponse
from app.services.verification import verify_claims

router = APIRouter()


@router.post("/verify", response_model=VerifyResponse)
def verify(request: VerifyRequest) -> VerifyResponse:
    return verify_claims(request)
