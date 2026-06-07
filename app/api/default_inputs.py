from fastapi import APIRouter

from app.schemas.default_inputs import DefaultInputsResponse
from app.services.default_inputs import load_default_inputs

router = APIRouter()


@router.get("/default-inputs", response_model=DefaultInputsResponse)
def default_inputs() -> DefaultInputsResponse:
    return load_default_inputs()
