from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings
from app.schemas.report import (
    ProjectMetadata,
    ReportInputBundle,
    ReportResponse,
    ReportSummary,
    RiskItem,
)


SYSTEM_VERSION = "0.1.0"


def assemble_report(bundle: ReportInputBundle) -> ReportResponse:
    risks = build_risks(bundle)
    summary = build_report_summary(bundle, risks)
    repo_url = bundle.repo_url or (
        bundle.repository_analysis.repo_url if bundle.repository_analysis else None
    )

    return ReportResponse(
        project_metadata=ProjectMetadata(
            projectId=bundle.project_id,
            repoUrl=repo_url,
            generatedAt=datetime.now(timezone.utc),
            systemVersion=SYSTEM_VERSION,
            modelVersions=model_versions(),
        ),
        summary=summary,
        claims=build_claims_section(bundle),
        detection=build_detection_section(bundle),
        verification=bundle.verification.model_dump(by_alias=True),
        transcript=build_transcript_section(bundle),
        repository=build_repository_section(bundle),
        company_relevance=bundle.company_relevance,
        risks_and_gaps={
            "items": [risk.model_dump() for risk in risks],
            "riskCount": len(risks),
        },
        evaluation_notes={
            "notes": bundle.evaluation_notes,
            "generatedNotes": generated_notes(bundle, risks),
        },
    )


def build_report_summary(bundle: ReportInputBundle, risks: list[RiskItem]) -> ReportSummary:
    verification_summary = bundle.verification.summary
    detected_count = (
        len(bundle.repository_analysis.detected_techs)
        if bundle.repository_analysis
        else count_detected_from_verification(bundle)
    )
    transcript_chunks = len(bundle.transcription.chunks) if bundle.transcription else 0
    return ReportSummary(
        totalClaims=verification_summary.total_claims,
        verifiedClaims=verification_summary.verified,
        partialClaims=verification_summary.partial,
        unverifiedClaims=verification_summary.unverified,
        contradictedClaims=verification_summary.contradicted,
        detectedTechnologies=detected_count,
        transcriptChunks=transcript_chunks,
        riskLevel=overall_risk_level(risks),
    )


def build_claims_section(bundle: ReportInputBundle) -> dict[str, Any]:
    if bundle.claim_extraction:
        return {
            "claimedTechs": [
                claim.model_dump(by_alias=True)
                for claim in bundle.claim_extraction.claimed_techs
            ],
            "summary": bundle.claim_extraction.summary.model_dump(by_alias=True),
            "descriptionProvided": bool(bundle.description),
        }

    return {
        "claimedTechs": [
            {
                "key": item.key,
                "name": item.claimed,
                "status": item.status,
                "confidence": item.confidence,
            }
            for item in bundle.verification.claim_verification
        ],
        "summary": {"claimCount": bundle.verification.summary.total_claims},
        "descriptionProvided": bool(bundle.description),
    }


def build_detection_section(bundle: ReportInputBundle) -> dict[str, Any]:
    if not bundle.repository_analysis:
        return {
            "detectedTechs": [],
            "summary": {"detectedCount": count_detected_from_verification(bundle)},
        }

    return {
        "detectedTechs": [
            tech.model_dump(by_alias=True)
            for tech in bundle.repository_analysis.detected_techs
        ],
        "summary": {
            "detectedCount": len(bundle.repository_analysis.detected_techs),
            "evidenceCount": bundle.repository_analysis.repository.evidence_count,
        },
    }


def build_transcript_section(bundle: ReportInputBundle) -> dict[str, Any]:
    if not bundle.transcription:
        return {
            "available": False,
            "chunkCount": 0,
            "duration": None,
            "qualityNotes": ["Transcript was not supplied to the report endpoint."],
        }

    return {
        "available": True,
        "duration": bundle.transcription.duration,
        "chunkCount": len(bundle.transcription.chunks),
        "preview": bundle.transcription.transcript[:500],
        "qualityNotes": [],
    }


def build_repository_section(bundle: ReportInputBundle) -> dict[str, Any]:
    if not bundle.repository_analysis:
        return {
            "available": False,
            "repoUrl": bundle.repo_url,
            "summary": None,
        }

    return {
        "available": True,
        "repoUrl": bundle.repository_analysis.repo_url,
        "summary": bundle.repository_analysis.repository.model_dump(by_alias=True),
    }


def build_risks(bundle: ReportInputBundle) -> list[RiskItem]:
    risks: list[RiskItem] = []
    verification_summary = bundle.verification.summary
    if verification_summary.contradicted:
        risks.append(
            RiskItem(
                severity="high",
                code="contradicted_claims",
                message=f"{verification_summary.contradicted} claimed technologies appear contradicted by supplied evidence.",
            )
        )
    if verification_summary.unverified:
        risks.append(
            RiskItem(
                severity="medium",
                code="unverified_claims",
                message=f"{verification_summary.unverified} claimed technologies were not supported by supplied evidence.",
            )
        )
    if verification_summary.partial:
        risks.append(
            RiskItem(
                severity="low",
                code="partial_claims",
                message=f"{verification_summary.partial} claimed technologies have only partial support.",
            )
        )
    if not bundle.transcription:
        risks.append(
            RiskItem(
                severity="medium",
                code="missing_transcript",
                message="Transcript output was not supplied, so video-claim corroboration is incomplete.",
            )
        )
    if not bundle.repository_analysis:
        risks.append(
            RiskItem(
                severity="medium",
                code="missing_repository_analysis",
                message="Repository analysis output was not supplied, so code evidence is incomplete.",
            )
        )
    if bundle.repository_analysis and bundle.repository_analysis.repository.truncated:
        risks.append(
            RiskItem(
                severity="medium",
                code="repository_scan_truncated",
                message="Repository scan hit the configured file limit, so detected technologies may be incomplete.",
            )
        )
    return risks


def generated_notes(bundle: ReportInputBundle, risks: list[RiskItem]) -> list[str]:
    notes = [
        "Report assembled from supplied endpoint outputs; no additional OpenAI calls were made by /api/report.",
    ]
    if not risks:
        notes.append("No major verification risks were identified in the supplied evidence.")
    if bundle.description:
        notes.append("Project description was included for traceability.")
    return notes


def overall_risk_level(risks: list[RiskItem]) -> str:
    severities = {risk.severity for risk in risks}
    if "high" in severities:
        return "high"
    if "medium" in severities:
        return "medium"
    if "low" in severities:
        return "low"
    return "low"


def count_detected_from_verification(bundle: ReportInputBundle) -> int:
    return sum(1 for item in bundle.verification.claim_verification if item.detected)


def model_versions() -> dict[str, str]:
    settings = get_settings()
    return {
        "whisper": settings.whisper_model,
        "embedding": settings.embedding_model,
        "agents": settings.agents_model,
    }
