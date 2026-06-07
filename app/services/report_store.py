from __future__ import annotations

import json
import re
from pathlib import Path

from app.schemas.report import ReportResponse, SavedReportItem


REPORTS_DIR = Path("reports")


def save_report(report: ReportResponse) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    project_id = report.project_metadata.project_id
    path = report_path(project_id)
    path.write_text(
        json.dumps(report.model_dump(by_alias=True, mode="json"), indent=2),
        encoding="utf-8",
    )
    return path


def load_report(project_id: str) -> ReportResponse | None:
    path = report_path(project_id)
    if not path.exists():
        return None

    data = json.loads(path.read_text(encoding="utf-8"))
    return ReportResponse(**data)


def list_reports() -> list[SavedReportItem]:
    if not REPORTS_DIR.exists():
        return []

    reports: list[SavedReportItem] = []
    for path in sorted(REPORTS_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            report = ReportResponse(**json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, ValueError):
            continue

        reports.append(
            SavedReportItem(
                projectId=report.project_metadata.project_id,
                repoUrl=report.project_metadata.repo_url,
                generatedAt=report.project_metadata.generated_at,
                riskLevel=report.summary.risk_level,
                totalClaims=report.summary.total_claims,
                verifiedClaims=report.summary.verified_claims,
                unverifiedClaims=report.summary.unverified_claims,
                contradictedClaims=report.summary.contradicted_claims,
                path=path.as_posix(),
            )
        )
    return reports


def report_path(project_id: str) -> Path:
    return REPORTS_DIR / f"{sanitize_report_id(project_id)}.json"


def sanitize_report_id(project_id: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_.-]+", "-", project_id.strip()).strip(".-")
    return sanitized[:120] or "report"
