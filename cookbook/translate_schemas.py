import marvin
from pydantic import BaseModel


class FooModel(BaseModel):
    identifier: str
    name: str


class BarModel(BaseModel):
    id: int
    first_name: str
    last_name: str


bar = marvin.cast(FooModel(identifier="42", name="Marvin Robot"), BarModel)

assert bar.model_dump() == {"id": 42, "first_name": "Marvin", "last_name": "Robot"}
