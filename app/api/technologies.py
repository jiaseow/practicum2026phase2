from collections import defaultdict

from fastapi import APIRouter

from app.schemas.technologies import TechnologiesResponse, TechnologyItem
from app.services.technologies import load_technologies

router = APIRouter()


@router.get("/technologies", response_model=TechnologiesResponse)
def technologies() -> TechnologiesResponse:
    techs = sorted(load_technologies().values(), key=lambda item: (item.category, item.name))
    items = [
        TechnologyItem(
            key=tech.key,
            name=tech.name,
            category=tech.category,
            confidenceTier=tech.confidence_tier,
            aliases=list(tech.aliases),
        )
        for tech in techs
    ]

    categories: dict[str, list[str]] = defaultdict(list)
    for tech in items:
        categories[tech.category].append(tech.key)

    return TechnologiesResponse(
        technologies=items,
        categories=dict(sorted(categories.items())),
        count=len(items),
    )
