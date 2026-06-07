from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.extract_claims import (
    ClaimedTechnology,
    ClaimExtractionSummary,
    ExtractClaimsRequest,
    ExtractClaimsResponse,
)
from app.services.technologies import Technology, load_technologies


QUOTE_RADIUS = 80
CLAIM_ALIAS_DENYLIST = {"next", "pg"}


@dataclass(frozen=True)
class AliasPattern:
    alias: str
    tech: Technology
    pattern: re.Pattern[str]


def extract_claims(request: ExtractClaimsRequest) -> ExtractClaimsResponse:
    description = request.description.strip()
    if not description:
        raise ValueError("description is required.")

    claimed_by_key: dict[str, ClaimedTechnology] = {}
    for alias_pattern in build_alias_patterns():
        match = alias_pattern.pattern.search(description)
        if not match or alias_pattern.tech.key in claimed_by_key:
            continue

        claimed_by_key[alias_pattern.tech.key] = ClaimedTechnology(
            key=alias_pattern.tech.key,
            name=alias_pattern.tech.name,
            category=alias_pattern.tech.category,
            matchedText=match.group(0),
            sourceQuote=extract_context(description, match.start(), match.end()),
            confidence="claimed",
        )

    claims = sorted(claimed_by_key.values(), key=lambda claim: (claim.category, claim.name))
    return ExtractClaimsResponse(
        projectId=request.project_id,
        claimedTechs=claims,
        summary=ClaimExtractionSummary(
            descriptionLength=len(description),
            claimCount=len(claims),
        ),
    )


def build_alias_patterns() -> list[AliasPattern]:
    aliases: list[tuple[str, Technology]] = []
    for tech in load_technologies().values():
        values = {tech.key, tech.name, *tech.aliases}
        aliases.extend((value, tech) for value in values if value)

    aliases.sort(key=lambda item: len(item[0]), reverse=True)
    return [
        AliasPattern(
            alias=alias,
            tech=tech,
            pattern=re.compile(rf"(?<![A-Za-z0-9_@/-]){re.escape(alias)}(?![A-Za-z0-9_@/-])", re.IGNORECASE),
        )
        for alias, tech in aliases
        if alias.lower() not in CLAIM_ALIAS_DENYLIST
    ]


def extract_context(text: str, start: int, end: int) -> str:
    quote_start = max(0, start - QUOTE_RADIUS)
    quote_end = min(len(text), end + QUOTE_RADIUS)
    quote = text[quote_start:quote_end].strip()
    quote = re.sub(r"\s+", " ", quote)
    if quote_start > 0:
        quote = "..." + quote
    if quote_end < len(text):
        quote = quote + "..."
    return quote
