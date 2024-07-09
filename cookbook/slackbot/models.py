from pydantic import BaseModel, Field


class Discovery(BaseModel):
    question: str = Field(description="the question the user is actually asking")
    prefect_version: str = Field(
        description="the version of Prefect the user is mentioning or using - allow rc versions",
        pattern=r"^\d+\.\d+\.\d+(?:\w+)?$",
    )


class ExcerptSummary(BaseModel):
    executive_summary: str = Field(description="at most 3 sentences summary")
    sources: list[str] = Field(
        default_factory=list, description="sources cited in summary"
    )
