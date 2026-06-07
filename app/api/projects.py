from fastapi import APIRouter

from app.schemas.projects import ProjectDeleteResponse, ProjectStatusResponse
from app.services.projects import delete_project, get_project_status

router = APIRouter()


@router.get("/projects/{project_id}", response_model=ProjectStatusResponse)
def project_status(project_id: str) -> ProjectStatusResponse:
    return get_project_status(project_id)


@router.delete("/projects/{project_id}", response_model=ProjectDeleteResponse)
def project_delete(project_id: str) -> ProjectDeleteResponse:
    return delete_project(project_id)
