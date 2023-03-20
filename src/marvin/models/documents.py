from pydantic import Field

from marvin.models.ids import DocumentID
from marvin.utilities.types import MarvinBaseModel


class Document(MarvinBaseModel):
    """A document."""

    type: str = Field(default="document")
    id: str = Field(default_factory=DocumentID.new)
    chroma_id: str = Field(None)
    text: str = Field(None)
    embedding: list[float] | None = Field(default=None)
    metadata: dict | None = Field(default=None)
