from pydantic import Field

from marvin.models.ids import DocumentID
from marvin.utilities.types import MarvinBaseModel


class Document(MarvinBaseModel):
    """A document."""

    id: str = Field(default_factory=DocumentID.new)
    text: str = Field(None)
    embedding: list[float] | None = Field(default=None)
    metadata: dict | None = Field(default=None)
