from pydantic import Field

from marvin.models.base import MarvinBaseModel


class Digest(MarvinBaseModel):
    ids: list[str] = Field(default_factory=list)
    documents: list[str] = Field(default_factory=list)
    embeddings: list[list[float]] | None = Field(default=None)
    metadatas: list[dict] = Field(default_factory=list)

    def __repr__(self):
        return (
            f"Digest(ids={len(self.ids)}, documents={len(self.documents)},"
            f" embeddings={'None' if not self.embeddings else len(self.embeddings)},"
            f" metadatas={len(self.metadatas)})"
        )
