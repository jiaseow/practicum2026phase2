from fastapi import APIRouter

from app.schemas.report import ReportInputBundle, ReportResponse, SavedReportsResponse
from app.services.report_store import list_reports, load_report, save_report
from app.services.reporting import assemble_report

router = APIRouter()


@router.post("/report", response_model=ReportResponse)
def report(request: ReportInputBundle) -> ReportResponse:
    response = assemble_report(request)
    save_report(response)
    return response


@router.get("/reports", response_model=SavedReportsResponse)
def get_reports() -> SavedReportsResponse:
    reports = list_reports()
    return SavedReportsResponse(reports=reports, count=len(reports))


@router.get("/reports/{project_id}", response_model=ReportResponse)
def get_report(project_id: str) -> ReportResponse:
    report_response = load_report(project_id)
    if report_response is None:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No saved report found for projectId: {project_id}",
        )
    return report_response
