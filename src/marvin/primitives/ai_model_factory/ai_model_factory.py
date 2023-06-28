from typing import TypeVar

from marvin.models.meta import DataSchema
from marvin.primitives.ai_model.ai_model import ai_model

T = TypeVar("T")

# If you're reading this and expected something fancier,
# I'm sorry to disappoint you. It's this simple.
AIModelFactory = ai_model(DataSchema)
