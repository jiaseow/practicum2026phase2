from pydantic import BaseModel, ConfigDict, Field


class ExtractClaimsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    description: str
    project_id: str = Field(..., alias="projectId")


class ClaimedTechnology(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    key: str
    name: str
    category: str
    matched_text: str = Field(alias="matchedText")
    source_quote: str = Field(alias="sourceQuote")
    confidence: str


class ClaimExtractionSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    description_length: int = Field(alias="descriptionLength")
    claim_count: int = Field(alias="claimCount")


class ExtractClaimsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: str = Field(alias="projectId")
    claimed_techs: list[ClaimedTechnology] = Field(alias="claimedTechs")
    summary: ClaimExtractionSummary
