from __future__ import annotations

from pydantic import BaseModel


class FutureModel(BaseModel):
    value: str


def build_future_model() -> FutureModel:
    return FutureModel(value="x")
