from typing import TypeVar

from marvin.components.ai_model.base import ai_model
from marvin.models.meta import DataSchema

T = TypeVar("T")

# If you're reading this and expected something fancier,
# I'm sorry to disappoint you. It's this simple.
AIModelFactory = ai_model(DataSchema)
