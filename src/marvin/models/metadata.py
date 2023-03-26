from pydantic import Field

from marvin.utilities.models import MarvinBaseModel, TimestampMixin


class Metadata(MarvinBaseModel, TimestampMixin):
    link: str = Field(default=None)
    title: str = Field(default="[untitled]")
    source: str = Field(default="unknown")
    document_type: str = Field(default="original")

    class Config:
        extra = "allow"
        arbitrary_types_allowed = True
