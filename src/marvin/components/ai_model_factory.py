from typing import Optional

from pydantic import BaseModel

from marvin.components.ai_model import ai_model


class DataSchema(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    properties: Optional[dict] = {}
    required: Optional[list[str]] = []
    additionalProperties: bool = False
    definitions: dict = {}
    description: Optional[str] = None


# If you're reading this and expected something fancier,
# I'm sorry to disappoint you. It's this simple.
AIModelFactory = ai_model(DataSchema)
