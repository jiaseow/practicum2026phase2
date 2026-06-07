from pydantic import BaseModel, ConfigDict, Field


class TechnologyItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    key: str
    name: str
    category: str
    confidence_tier: str = Field(alias="confidenceTier")
    aliases: list[str]


class TechnologiesResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    technologies: list[TechnologyItem]
    categories: dict[str, list[str]]
    count: int
