import asyncio
import functools
from typing import Optional, Type, TypeVar

from pydantic import BaseModel

from marvin.models.meta import DataSchema
from marvin.primitives.ai_model.ai_model import ai_model

T = TypeVar("T")

# If you're reading this and expected something fancier, 
# I'm sorry to disappoint you. It's this simple.

ai_model_factory = ai_model(DataSchema)

default = ai_model_factory