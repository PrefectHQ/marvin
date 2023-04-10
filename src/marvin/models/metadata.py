from pydantic import Field

from marvin.utilities.models import MarvinBaseModel


class Metadata(MarvinBaseModel):
    link: str = Field(default=None)
    title: str = Field(default="[untitled]")
    source: str = Field(default="unknown")
    document_type: str = Field(default="original")

    class Config:
        extra = "allow"
        arbitrary_types_allowed = True

    def __str__(self):
        lines = []
        for key, value in self.dict().items():
            if value is not None and value != "":
                lines.append(f"{key.capitalize()}: {value}")
        return "\n".join(lines)
