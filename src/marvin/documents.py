from pydantic import BaseModel, Field


class Document(BaseModel):
    """A document."""

    id: str = Field(...)
    text: str = Field(...)
    embedding: list[float] | None = Field(default=None)
    metadata: dict | None = Field(default=None)
