from typing import Optional

from pydantic import BaseModel


class DataSchema(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    properties: Optional[dict] = {}
    required: Optional[list[str]] = []
    additionalProperties: bool = False
    definitions: dict = {}
    description: Optional[str] = None