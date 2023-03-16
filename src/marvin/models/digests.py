from marvin.models.base import MarvinBaseModel
from pydantic import Field

class Digest(MarvinBaseModel):
    ids: list[str] = Field(default_factory=list)
    documents: list[str] = Field(default_factory=list)
    embeddings: list[list[float]] | None = Field(default=None)
    metadatas: list[dict] = Field(default_factory=list)