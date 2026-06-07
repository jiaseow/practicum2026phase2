from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.schemas.verify import (
    ClaimVerificationResult,
    VerificationEvidence,
    VerificationSummary,
    VerifyRequest,
    VerifyResponse,
)
from app.services.technologies import Technology, match_technology


DEPENDENCY_SOURCES = {
    "dependencies",
    "devDependencies",
    "peerDependencies",
    "optionalDependencies",
    "requirements",
    "pyproject",
}
REPO_SOURCES = DEPENDENCY_SOURCES | {"dockerfile", "docker-compose", "workflow", "import", "package-script"}
NEGATION_WINDOW = 48


@dataclass
class NormalizedClaim:
    key: str
    name: str
    category: str


@dataclass
class NormalizedDetection:
    key: str
    name: str
    confidence: str
    evidence: list[VerificationEvidence] = field(default_factory=list)
    sources: set[str] = field(default_factory=set)


def verify_claims(request: VerifyRequest) -> VerifyResponse:
    claims = normalize_claims(request.claimed_techs)
    detections = normalize_detections(request.detected_techs)

    results = [
        verify_single_claim(claim, detections.get(claim.key), request.transcript_chunks)
        for claim in claims
    ]
    summary = build_summary(results)
    return VerifyResponse(
        projectId=request.project_id,
        claimVerification=results,
        summary=summary,
    )


def normalize_claims(raw_claims: list[Any]) -> list[NormalizedClaim]:
    claims_by_key: dict[str, NormalizedClaim] = {}
    for item in raw_claims:
        tech = technology_from_item(item)
        if tech is None:
            continue
        claims_by_key[tech.key] = NormalizedClaim(
            key=tech.key,
            name=tech.name,
            category=tech.category,
        )
    return sorted(claims_by_key.values(), key=lambda claim: (claim.category, claim.name))


def normalize_detections(raw_detections: list[Any]) -> dict[str, NormalizedDetection]:
    detections: dict[str, NormalizedDetection] = {}
    for item in raw_detections:
        tech = technology_from_item(item)
        if tech is None:
            continue

        detection = detections.setdefault(
            tech.key,
            NormalizedDetection(
                key=tech.key,
                name=tech.name,
                confidence=read_string(item, "confidence") or "medium",
            ),
        )
        for evidence in read_list(item, "evidence"):
            normalized = normalize_repo_evidence(evidence)
            detection.evidence.append(normalized)
            detection.sources.add(normalized.source)
    return detections


def verify_single_claim(
    claim: NormalizedClaim,
    detection: NormalizedDetection | None,
    transcript_chunks,
) -> ClaimVerificationResult:
    evidence: list[VerificationEvidence] = []
    notes: list[str] = []
    detected = detection is not None
    transcript_evidence = find_transcript_mentions(claim.name, transcript_chunks)
    transcript_mentioned = bool(transcript_evidence)
    contradicted = has_transcript_contradiction(claim.name, transcript_chunks)

    if detection:
        evidence.extend(detection.evidence[:6])
    evidence.extend(transcript_evidence[:3])

    if contradicted and not detected:
        status = "contradicted"
        confidence = 0.2
        notes.append("Transcript contains a nearby negation for this claimed technology.")
    elif detected and transcript_mentioned:
        status = "verified"
        confidence = confidence_from_detection(detection)
    elif detected:
        status = "partial"
        confidence = min(confidence_from_detection(detection), 0.75)
        notes.append("Repository evidence found, but no transcript mention was provided.")
    elif transcript_mentioned:
        status = "partial"
        confidence = 0.4
        notes.append("Transcript mention found, but repository evidence was not provided.")
    else:
        status = "unverified"
        confidence = 0.1
        notes.append("No repository or transcript evidence matched this claim.")

    return ClaimVerificationResult(
        key=claim.key,
        claimed=claim.name,
        detected=detected,
        transcriptMentioned=transcript_mentioned,
        status=status,
        confidence=confidence,
        evidence=evidence,
        notes=notes,
    )


def technology_from_item(item: Any) -> Technology | None:
    if isinstance(item, str):
        return match_technology(item)
    if isinstance(item, dict):
        for key in ("key", "name", "claimed"):
            value = item.get(key)
            if isinstance(value, str):
                tech = match_technology(value)
                if tech is not None:
                    return tech
    return None


def normalize_repo_evidence(item: Any) -> VerificationEvidence:
    if not isinstance(item, dict):
        return VerificationEvidence(source="repository", detail=str(item))

    source = str(item.get("source") or "repository")
    file_path = item.get("file")
    line = item.get("line")
    snippet = item.get("snippet")
    detail_parts = [source]
    if file_path:
        detail_parts.append(str(file_path))
    if line:
        detail_parts.append(f"line {line}")
    return VerificationEvidence(
        source=source,
        detail=" / ".join(detail_parts),
        file=str(file_path) if file_path else None,
        line=int(line) if isinstance(line, int) else None,
        snippet=str(snippet) if snippet else None,
    )


def find_transcript_mentions(tech_name: str, transcript_chunks) -> list[VerificationEvidence]:
    pattern = compile_tech_pattern(tech_name)
    matches: list[VerificationEvidence] = []
    for chunk in transcript_chunks:
        if not pattern.search(chunk.text):
            continue
        matches.append(
            VerificationEvidence(
                source="transcript",
                detail=f"Transcript mention of {tech_name}",
                snippet=extract_match_context(chunk.text, pattern),
                chunkId=chunk.id,
                startTime=chunk.start_time,
                endTime=chunk.end_time,
            )
        )
    return matches


def has_transcript_contradiction(tech_name: str, transcript_chunks) -> bool:
    pattern = compile_tech_pattern(tech_name)
    negation = re.compile(r"\b(no|not|never|without|did not|does not|isn't|is not|aren't|are not)\b", re.IGNORECASE)
    for chunk in transcript_chunks:
        for match in pattern.finditer(chunk.text):
            start = max(0, match.start() - NEGATION_WINDOW)
            end = min(len(chunk.text), match.end() + NEGATION_WINDOW)
            if negation.search(chunk.text[start:end]):
                return True
    return False


def compile_tech_pattern(tech_name: str) -> re.Pattern[str]:
    escaped = re.escape(tech_name).replace(r"\.", r"\.?")
    return re.compile(rf"(?<![A-Za-z0-9_@/-]){escaped}(?![A-Za-z0-9_@/-])", re.IGNORECASE)


def extract_match_context(text: str, pattern: re.Pattern[str]) -> str:
    match = pattern.search(text)
    if not match:
        return text[:160]
    start = max(0, match.start() - 70)
    end = min(len(text), match.end() + 70)
    context = re.sub(r"\s+", " ", text[start:end].strip())
    if start > 0:
        context = "..." + context
    if end < len(text):
        context += "..."
    return context


def confidence_from_detection(detection: NormalizedDetection | None) -> float:
    if detection is None:
        return 0.1
    if detection.sources & DEPENDENCY_SOURCES:
        return 0.9
    if detection.sources & REPO_SOURCES:
        return 0.7
    if detection.confidence == "high":
        return 0.8
    if detection.confidence == "medium":
        return 0.6
    return 0.4


def build_summary(results: list[ClaimVerificationResult]) -> VerificationSummary:
    counts = {"verified": 0, "partial": 0, "unverified": 0, "contradicted": 0}
    for result in results:
        counts[result.status] += 1
    return VerificationSummary(
        totalClaims=len(results),
        verified=counts["verified"],
        partial=counts["partial"],
        unverified=counts["unverified"],
        contradicted=counts["contradicted"],
    )


def read_string(item: Any, key: str) -> str | None:
    return item.get(key) if isinstance(item, dict) and isinstance(item.get(key), str) else None


def read_list(item: Any, key: str) -> list[Any]:
    return item.get(key, []) if isinstance(item, dict) and isinstance(item.get(key), list) else []
