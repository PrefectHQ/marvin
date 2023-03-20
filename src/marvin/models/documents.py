from pydantic import Field

from marvin.utilities.types import MarvinBaseModel


class Document(MarvinBaseModel):
    """A document."""

    id: str = Field(...)
    text: str = Field(None)
    embedding: list[float] | None = Field(default=None)
    metadata: dict | None = Field(default=None)
